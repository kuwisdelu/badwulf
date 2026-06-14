
# Synchronize files and directories across work sites

import os
import io
import json
import socket
import subprocess

from collections.abc import MutableMapping
from dataclasses import dataclass
from dataclasses import asdict

from .rssh import rssh
from .util import mkpath
from .util import prune

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

	def resolve_node(self, host: str) -> str:
		"""
		Resolve a node alias from a hostname
		:param host: The hostname
		:raises ValueError: If the hostname isn't a known node
		:returns: The node alias
		"""
		host = host.casefold()
		for k, v in self.hosts.items():
			v = v.casefold()
			if v in (host, f"{host}.local"):
				return k
		raise ValueError(f"no known node for host {host}")

	def resolve_prefix(self, path: str) -> str:
		"""
		Resolve a prefix alias from a filepath
		:param path: The filepath
		:raises ValueError: If the filepath isn't in a known prefix
		:returns: The prefix alias
		"""
		path = mkpath(path)
		for k, v in self.paths.items():
			v = mkpath(v)
			if v == os.path.commonpath((v, path)):
				return k
		raise ValueError(f"no known prefix for path {path}")

	def detect_node(self) -> str:
		"""
		Resolve node alias of localhost
		:raises ValueError: If the hostname isn't a known node
		:returns: The node alias
		"""
		self.resolve_node(socket.gethostname())

	def detect_prefix(self) -> str:
		"""
		Resolve a prefix alias from current working directory
		:raises ValueError: If the filepath isn't in a known prefix
		:returns: The prefix alias
		"""
		self.resolve_prefix(os.getcwd())

class syncer(MutableMapping):
	"""
	Sync projects and data between sites
	"""

	def __init__(self, 
		sites: dict[str, profile], 
		local: str = "local"):
		"""
		Initializes a syncer instance
		:param sites: Mapping of aliases-to-sites
		:param local: Name of the local site
		"""
		if local not in sites:
			raise ValueError(f"missing required site '{local}'")
		self._sites = sites
		self._local = local

	def __getitem__(self, key: str) -> profile:
		"""
		Get a site profile
		"""
		return self._sites[key]

	def __setitem__(self, key: str, value: profile) -> None:
		"""
		Set a site profile
		"""
		self._sites[key] = value

	def __delitem__(self, key: str) -> None:
		"""
		Delete a site profile
		"""
		del self._sites[key]

	def __len__(self) -> int:
		"""
		Get the number of sites
		"""
		return len(self._sites)

	def __iter__(self):
		"""
		Get an iterator over the site profiles
		"""
		return iter(self._sites)

	@property
	def local(self):
		"""
		Get the local site
		"""
		return self._sites[self._local]

	def push(self, 
		site: str,
		path: str,
		host_ref: str = "default",
		path_ref: str = "default",
		**kwargs: dict[str, bool]) -> subprocess.CompletedProcess:
		"""
		Push a file or directory to another site (via rsync)
		:param site: The other site
		:param path: A relative file or directory path to sync
		:param host_ref: (Optional) The other host alias
		:param path_ref: (Optional) The anchor path alias
		:param kwargs: Additional arguments for rssh.push
		"""
		has_trailing_slash = True if path[-1] == "/" else False
		src = os.path.join(self.local.paths[path_ref], path)
		dst = os.path.join(self[site].paths[path_ref], path)
		if has_trailing_slash:
			src += "/"
			dst += "/"
		con = self.bridge(site, host_ref)
		return con.push(src=src, dst=dst, **kwargs)

	def pull(self,
		site: str, 
		path: str,
		host_ref: str = "default",
		path_ref: str = "default",
		**kwargs: dict[str, bool]) -> subprocess.CompletedProcess:
		"""
		Pull a file or directory from another site (via rsync)
		:param site: The other site
		:param path: A relative file or directory path to sync
		:param host_ref: (Optional) The other host alias
		:param path_ref: (Optional) The anchor path alias
		:param kwargs: Additional arguments for rssh.push
		"""
		has_trailing_slash = True if path[-1] == "/" else False
		src = os.path.join(self[site].paths[path_ref], path)
		dst = os.path.join(self.local.paths[path_ref], path)
		if has_trailing_slash:
			src += "/"
			dst += "/"
		con = self.bridge(site, host_ref)
		return con.pull(src=src, dst=dst, **kwargs)

	def bridge(self, site: str, host_ref: str = "default") -> rssh:
		"""
		Get an rssh object to a host at another site
		:param site: The other site name
		:param host_ref: (Optional) The other host alias
		:raises ValueError: On attempt to connect to the local site
		:returns: An rssh object
		"""
		site = self[site]
		return rssh(
			user=site.user,
			host=site.hosts[host_ref],
			proxy_user=site.proxy.get("user"),
			proxy_host=site.proxy.get("host"))

	def to_dict(self) -> dict[str: Any]:
		"""
		Format safely for serialization (to json)
		:returns: A dict representation
		"""
		return prune({k: asdict(v) for k, v in self.items()})

	@classmethod
	def from_dict(cls, d: dict[str: Any]):
		"""
		Create a syncer from a dict
		:param d: A dict (parsed from json)
		:returns: An syncer object
		"""
		return cls({k: profile(**v) for k, v in d.items()})

	@classmethod
	def from_file(cls, f: io.TextIOBase | io.BufferedIOBase):
		"""
		Create a syncer from a json file
		:param f: An open json file
		:returns: A syncer object
		"""
		return cls.from_dict(json.load(f))

	@classmethod
	def from_path(cls, p: str):
		"""
		Create a syncer from a json file
		:param p: The path to the json file
		:returns: A syncer object
		"""
		p = mkpath(p, must_exist=True)
		with open(p) as f:
			return cls.from_file(f)
