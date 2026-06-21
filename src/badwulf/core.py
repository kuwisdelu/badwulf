
# Synchronize files and directories across work sites

import os
import io
import json
import socket
import subprocess

from collections.abc import MutableMapping
from dataclasses import dataclass
from dataclasses import asdict

from .db import projdb
from .rssh import rssh
from .util import detect
from .util import mkpath
from .util import prune

LOCAL_SITE = "local"
DEFAULT_HOST = "default"
DEFAULT_PREFIX = "default"

@dataclass
class profile:
	"""
	Profile information for a work site
	:ivar user: Username for work site authentication
	:ivar hosts: Dict of aliases-to-hosts ('default': 'localhost', etc.)
	:ivar paths: Dict of aliases-to-paths ('default': '$HOME/projects', etc.)
	:ivar proxy: Dict of 'host' and 'user' for a proxy jump
	"""
	user: str | None = None
	hosts: dict[str, str | None] | None = None
	paths: dict[str, str | None] | None = None
	proxy: dict[str, str | None] | None = None

	def __post_init__(self):
		if self.user is None:
			self.user = ""
		if self.hosts is None:
			self.hosts = {}
		if self.paths is None:
			self.paths = {}
		if self.proxy is None:
			self.proxy = {}

	def alias_of_host(self, host: str) -> str:
		"""
		Resolve a host alias from a hostname
		:param host: The hostname
		:raises ValueError: If a known host isn't found
		:returns: The host alias
		"""
		host = host.casefold()
		for k, v in self.hosts.items():
			v = v.casefold()
			if v in (host, f"{host}.local"):
				return k
		raise ValueError(f"not a known host: {host}")

	def alias_of_path(self, path: str, parents: bool = False) -> str:
		"""
		Resolve a path alias from a filepath
		:param path: The filepath
		:param parents: Consider parent directories of filepath?
		:raises ValueError: If a known path isn't found
		:returns: The path alias
		"""
		path = mkpath(path)
		for k, v in self.paths.items():
			v = mkpath(v)
			if parents:
				test = os.path.commonpath((v, path))
			else:
				test = path
			if v == test:
				return k
		raise ValueError(f"not a known path: {path}")

@dataclass
class profiles(MutableMapping):
	"""
	Collection of work site profiles
	:ivar sites: Mapping of aliases-to-sites
	"""
	sites: dict[str, profile]

	def __getitem__(self, key: str) -> profile:
		"""
		Get a site profile
		"""
		return self.sites[key]

	def __setitem__(self, key: str, value: profile) -> None:
		"""
		Set a site profile
		"""
		self.sites[key] = value

	def __delitem__(self, key: str) -> None:
		"""
		Delete a site profile
		"""
		del self.sites[key]

	def __len__(self) -> int:
		"""
		Get the number of sites
		"""
		return len(self.sites)

	def __iter__(self):
		"""
		Get an iterator over the site profiles
		"""
		return iter(self.sites)

	def to_dict(self) -> dict[str: Any]:
		"""
		Format safely for serialization (to json)
		:returns: A dict representation
		"""
		return prune({k: asdict(v) for k, v in self.items()})

	@classmethod
	def from_dict(cls, d: dict[str: Any]):
		"""
		Create site profiles from a dict
		:param d: A dict (parsed from json)
		:returns: An profiles object
		"""
		return cls({k: profile(**v) for k, v in d.items()})

	@classmethod
	def from_file(cls, f: io.TextIOBase | io.BufferedIOBase):
		"""
		Create site profiles from a json file
		:param f: An open json file
		:returns: A profiles object
		"""
		return cls.from_dict(json.load(f))

	@classmethod
	def from_path(cls, p: str):
		"""
		Create site profiles from a json file
		:param p: The path to the json file
		:returns: A profiles object
		"""
		p = mkpath(p, must_exist=True)
		with open(p) as f:
			return cls.from_file(f)

class dbsyncer:
	"""
	Sync projects and data between sites
	"""
	def __init__(self, 
		path: str, 
		sites: dict[str, profile] | None = None):
		"""
		Initializes dbsyncer from a json file or from defaults
		:param path: Path to the json file defining sites
		:param sites: A profiles object mapping aliases-to-sites
		"""
		self.path = mkpath(path)
		if sites is None:
			self.load_sites()
		else:
			self.sites = sites

	@property
	def local(self) -> profile:
		"""
		Get the local work site profile
		"""
		return self.sites[LOCAL_SITE]

	def resolve(self,
		site: str | None = None, 
		host: str | None = None,
		prefix: str | None = None) -> tuple[str]:
		"""
		Resolve valid aliases for the tracked databases
		:returns: A tuple of site, host, prefix
		"""
		if site is None:
			site = LOCAL_SITE
		if site not in self.sites:
			raise KeyError(f"unknown site: {site}")
		if host is None and len(self.sites[site].hosts) > 0:
			host = DEFAULT_HOST
		if host is not None and host not in self.sites[site].hosts:
			raise KeyError(f"unknown host: {host}")
		if prefix is None:
			prefix = DEFAULT_PREFIX
		if prefix not in self.sites[site].paths:
			raise KeyError(f"unknown prefix: {prefix}")
		return site, host, prefix

	def get(self, 
		site: str | None = None, 
		host: str | None = None,
		prefix: str | None = None) -> projdb:
		"""
		Get a project database for a site, host, and prefix
		:param site: The site name (if not local)
		:param host: The host alias (if not default)
		:param prefix: The prefix alias (if not default)
		:returns: A projdb object
		"""
		site, host, prefix = self.resolve(site, host, prefix)
		if site == LOCAL_SITE:
			root = self.local.paths[prefix]
			manifest = "manifest.json"
		else:
			root = None
			if host is None:
				manifest = os.path.join(
					self.local.paths[prefix],
					f"manifest-{site}.json")
			else:
				manifest = os.path.join(
					self.local.paths[prefix],
					f"manifest-{site}-{host}.json")
		return projdb(root=root, manifest=manifest)

	def bridge(self, site: str, host: str | None = None) -> rssh:
		"""
		Get an rssh object to another site
		:param site: The site name
		:param host: The host alias (if remote and not default)
		:returns: An rssh object
		"""
		site = self.sites[site]
		if host is None and len(site.hosts) > 0:
			host = site.hosts[DEFAULT_HOST]
		else:
			host = site.hosts[host]
		return rssh(
			user=site.user,
			host=host,
			proxy_user=site.proxy.get("user"),
			proxy_host=site.proxy.get("host"))

	def load_sites(self) -> None:
		"""
		Load the work site profiles
		"""
		if os.path.exists(self.path):
			self.sites = profiles.from_path(self.path)
		else:
			self.sites = profiles({LOCAL_SITE: profile()})

	def save_sites(self, indent="\t") -> None:
		"""
		Save the work site profiles
		"""
		with open(self.path, "w") as f:
			json.dump(self.sites.to_dict(), f, indent=indent)

	@classmethod
	def from_default_locations(cls):
		"""
		Attempts to initialize from the following locations:
		1. $BADWULF_SITES 
		2. ~/.badwulf-sites.json
		3. ~/.badwulf/.badwulf-sites.json 
		and creates default prefix at (3) if none exist
		"""
		if "BADWULF_SITES" in os.environ:
			return cls(os.getenv("BADWULF_SITES"))
		try:
			path = detect(r"^\.?badwulf-sites\.json$", 
				"~", mkpath("~", ".badwulf"))
			return cls(path)
		except FileNotFoundError:
			prefix = mkpath("~", ".badwulf")
			if not os.path.isdir(prefix):
				mktree(prefix)
			path = mkpath(prefix, "badwulf-sites.json")
			site = profile(paths={DEFAULT_PREFIX: prefix})
			sites = profiles({LOCAL_SITE: site})
			dbs = cls(path, sites=sites)
			dbs.save_sites()
			return dbs
