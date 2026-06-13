
# Synchronize files and directories across work sites

import os
import io
import json
import subprocess
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

class syncer:
	"""
	Sync projects and data between sites
	"""

	def __init__(self, 
		sites: dict[str, profile], 
		local: str = "self"):
		"""
		Initializes a syncer instance
		:param sites: Mapping of aliases-to-sites
		:param local: Name of the local site
		"""
		self.sites = sites
		if local not in sites:
			raise ValueError(f"missing required site '{local}'")
		self.local = local

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
		src = os.path.join(self.sites[self.local].paths[path_ref], path)
		dst = os.path.join(self.sites[site].paths[path_ref], path)
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
		src = os.path.join(self.sites[site].paths[path_ref], path)
		dst = os.path.join(self.sites[self.local].paths[path_ref], path)
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
		if site == self.local:
			raise ValueError(f"expected another site (not '{self.local}')")
		site = self.sites[site]
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
		return prune({k: asdict(v) for k, v in self.sites.items()})

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
