
# Synchronize files and directories across work sites

import os
import io
import json
import socket
import subprocess

from collections.abc import MutableMapping
from dataclasses import dataclass
from dataclasses import asdict
from dataclasses import replace

from .db import projdb
from .rssh import rssh
from .util import detect
from .util import mkpath
from .util import prune

BADWULF_SITES = os.getenv("BADWULF_SITES", None)
BADWULF_LOCAL = os.getenv("BADWULF_LOCAL", "local")
DEFAULT_ALIAS = "default"

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

	def normalize_host_alias(self, alias: str | None) -> str | None:
		"""
		Normalize a host alias
		:param alias: A possible host alias or None
		:raises KeyError: If the alias is invalid
		:returns: A valid host alias (or None if no hosts)
		"""
		if alias is None and len(self.hosts) > 0:
			alias = DEFAULT_ALIAS
		if alias is not None and alias not in self.hosts:
			raise KeyError(f"unknown host alias: {alias}")
		else:
			return alias

	def normalize_path_alias(self, alias: str | None) -> str:
		"""
		Normalize a path alias
		:param alias: A possible path alias or None
		:raises KeyError: If the alias is invalid
		:returns: A valid path alias
		"""
		if alias is None:
			alias = DEFAULT_ALIAS
		if alias not in self.paths:
			raise KeyError(f"unknown path alias: {alias}")
		else:
			return alias

	def get_host(self, alias: str | None) -> str | None:
		"""
		Get a host by its alias, after normalizing
		:param alias: A host alias
		:raises KeyError: If normalization fails
		:returns: A hostname (or None if no hosts)
		"""
		return self.hosts.get(self.normalize_host_alias(alias))

	def get_path(self, alias: str | None) -> str:
		"""
		Get a path by its alias, after normalizing
		:param alias: A path alias
		:raises KeyError: If normalization fails
		:returns: A filepath
		"""
		return self.paths.get(self.normalize_path_alias(alias))

	def set_default_host(self, host: str | None) -> None:
		"""
		Set (or unset) the default host for a site profile
		:param host: A hostname
		"""
		if host is None and DEFAULT_ALIAS in self.hosts:
			del self.hosts[DEFAULT_ALIAS]
		else:
			self.hosts[DEFAULT_ALIAS] = host

	def set_default_path(self, path: str | None) -> None:
		"""
		Set (or unset) the default path for a site profile
		:param path: A filepath
		"""
		if path is None and DEFAULT_ALIAS in self.paths:
			del self.paths[DEFAULT_ALIAS]
		else:
			self.paths[DEFAULT_ALIAS] = path

	def get_host_alias_for(self, host: str) -> str:
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

	def get_path_alias_for(self, path: str, parents: bool = False) -> str:
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
		sites: profiles | None = None,
		sites_path: str = "badwulf-sites.json",
		local_name: str = BADWULF_LOCAL):
		"""
		Initializes dbsyncer from a json file or from defaults
		:param path: Path to the json file defining sites
		:param sites: A profiles object mapping aliases-to-sites
		"""
		self.sites = sites
		self.sites_path = mkpath(sites_path)
		self.local_name = local_name
		self._db = {}

	@property
	def local(self) -> profile:
		"""
		Get the local work site profile
		"""
		return self.sites[self.local_name]

	@local.setter
	def local(self, value: profile) -> None:
		"""
		Set the local work site profile
		"""
		self.sites[self.local_name] = value

	def local_db(self, prefix: str | None = None) -> projdb:
		"""
		Get the local path for a prefix
		"""
		return self.get_db(self.local_name, None, prefix)

	def local_prefix(self, prefix: str | None = None) -> str:
		"""
		Get the local path for a prefix
		"""
		return self.local.get_path(prefix)

	def load_sites(self) -> None:
		"""
		Load the work site profiles
		"""
		self.sites = profiles.from_path(self.sites_path)

	def save_sites(self, indent="\t") -> None:
		"""
		Save the work site profiles
		"""
		with open(self.path, "w") as f:
			json.dump(self.sites.to_dict(), f, indent=indent)

	def ensure_sites(self) -> None:
		"""
		Ensure work site profiles are loaded and persisted
		"""
		if os.path.exists(self.sites_path):
			self.load_sites()
		else:
			if self.sites is None:
				prefix = os.path.dirname(self.sites_path)
				self.local = profile()
				self.local.set_default_path(prefix)
			self.save_sites()

	def normalize_site_name(self, site: str | None) -> str:
		"""
		Normalize a site name
		:param site: A possible site name or None
		:raises KeyError: If the name is invalid
		:returns: A valid site name
		"""
		if site is None:
			site = self.local_name
		if site not in self.sites:
			raise KeyError(f"unknown site: {site}")
		else:
			return site

	def get_site(self, site: str | None) -> str:
		"""
		Get a site profile by its name, after normalizing
		:param site: A site name
		:raises KeyError: If normalization fails
		:returns: A site profile
		"""
		return self.sites.get(self.normalize_site_name(site))

	def get_syncer(self, site: str, host: str | None = None) -> rssh:
		"""
		Get an rssh object to a node at another site
		:param site: The site name
		:param host: The host alias (if remote and not default)
		:returns: An rssh object
		"""
		site = self.get_site(site)
		return rssh(
			user=site.user,
			host=site.get_host(host),
			proxy_user=site.proxy.get("user"),
			proxy_host=site.proxy.get("host"))

	def get_db(self, 
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
		site = self.normalize_site_name(site)
		host = self.get_site(site).normalize_host_alias(host)
		if site == self.local_name:
			root = self.local.get_path(prefix)
			manifest = os.path.join(root, "manifest.json")
		else:
			root = None
			if host is None:
				filename =f"manifest-{site}.json"
			else:
				filename = f"manifest-{site}-{host}.json"
			manifest = os.path.join(self.local.get_path(prefix), filename)
		dbkey = (root, manifest)
		if dbkey not in self._db:
			self._db[dbkey] = projdb(root=root, manifest=manifest)
			self._db[dbkey].refresh()
		return self._db[dbkey]

	def get_prefix(self, 
		site: str | None = None, 
		prefix: str | None = None) -> str:
		"""
		Get the site prefix for a project database
		"""
		return self.get_site(site).get_path(prefix)

	def pull_manifest(self, 
		site: str, 
		host: str | None = None,
		prefix: str | None = None,
		**kwargs: Any) -> None:
		"""
		Pull a manifest from a node at another site
		:param site: The site name
		:param host: The host alias (if not default)
		:param prefix: The prefix alias (if not default)
		:param kwargs: Arguments passed to rssh.pull
		"""
		sync = self.get_syncer(site, host)
		src = os.path.join(self.get_prefix(site, prefix), "manifest.json")
		dst = self.get_db(site, host, prefix).manifest
		return sync.pull(src=src, dst=dst, **kwargs)

	def push_manifest(self, 
		site: str, 
		host: str | None = None,
		prefix: str | None = None,
		**kwargs: Any) -> None:
		"""
		Push a manifest to a node at another site
		:param site: The site name
		:param host: The host alias (if not default)
		:param prefix: The prefix alias (if not default)
		:param kwargs: Arguments passed to rssh.pull
		"""
		sync = self.get_syncer(site, host)
		src = self.get_db(site, host, prefix).manifest
		dst = os.path.join(self.get_prefix(site, prefix), "manifest.json")
		return sync.pull(src=src, dst=dst, **kwargs)

	def pull_tree(self, 
		name: str,
		site: str, 
		host: str | None = None,
		prefix: str | None = None,
		**kwargs: Any) -> None:
		"""
		Pull a project from a node at another site
		:param name: The project name
		:param site: The site name
		:param host: The host alias (if not default)
		:param prefix: The prefix alias (if not default)
		:param kwargs: Arguments passed to rssh.pull
		"""
		sync = self.get_syncer(site, host)
		remote_db = self.get_db(site, host, prefix)
		try:
			proj = remote_db[name]
		except KeyError:
			raise KeyError(f"no project in manifest named '{name}'")
		src = proj.path
		if src[-1] != "/":
			src += "/"
		dst = os.path.join(self.local_prefix(prefix), proj.canonical_path)
		local_db = self.local_db(prefix)
		local_db[name] = replace(proj, path=dst)
		local_db.save()
		return sync.pull(src=src, dst=dst, **kwargs)

	def push_tree(self, 
		name: str,
		site: str, 
		host: str | None = None,
		prefix: str | None = None,
		**kwargs: Any) -> None:
		"""
		Push a project to a node at another site
		:param name: The project name
		:param site: The site name
		:param host: The host alias (if not default)
		:param prefix: The prefix alias (if not default)
		:param kwargs: Arguments passed to rssh.push
		"""
		sync = self.get_syncer(site, host)
		local_db = self.local_db(prefix)
		try:
			proj = local_db[name]
		except KeyError:
			raise KeyError(f"no project in manifest named '{name}'")
		src = proj.path
		if src[-1] != "/":
			src += "/"
		dst = os.path.join(self.get_prefix(site, prefix), proj.canonical_path)
		remote_db = self.get_db(site, host, prefix)
		remote_db[name] = replace(proj, path=dst)
		remote_db.save()
		return sync.push(src=src, dst=dst, **kwargs)

	@classmethod
	def from_path(cls, p: str):
		"""
		Create a dbsyncer from a json file and load sites
		"""
		dbs = cls(sites_path=mkpath(p, must_exist=True))
		dbs.ensure_sites()
		return dbs

	@classmethod
	def from_default_locations(cls):
		"""
		Attempts to initialize from the following locations:
		1. $BADWULF_SITES 
		2. ~/.badwulf-sites.json
		3. ~/.badwulf/.badwulf-sites.json 
		and defaults to (3) if none exist
		"""
		sites_path = BADWULF_SITES
		if sites_path is None:
			try:
				sites_path = detect(r"^\.?badwulf-sites\.json$", 
					"~", mkpath("~", ".badwulf"))
			except FileNotFoundError:
				prefix = mkpath("~", ".badwulf")
				if not os.path.isdir(prefix):
					mktree(prefix)
				sites_path = mkpath(prefix, "badwulf-sites.json")
		dbs = cls(sites_path=sites_path)
		dbs.ensure_sites()
		return dbs
