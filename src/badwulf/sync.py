
# Synchronize files and directories across work sites

import os
import io
import json
import subprocess
from dataclasses import dataclass
from dataclasses import asdict

from .rssh import rssh
from .tools import fix_path
from .tools import prune

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
	Sync projects and datasets between sites
	"""

	def __init__(self, sites: dict[str, profile]):
		"""
		Initializes a syncer instance
		:param sites: Mapping of aliases-to-sites
		"""
		self.sites = sites
		if "self" not in self.sites:
			raise ValueError("missing required site 'self'")

	def node(self, site: str, host_ref: str = "default") -> rssh:
		"""
		Get an rssh object for a node at another site
		:param site: The other site name
		:param host_ref: (Optional) The other host alias
		:returns: An rssh object
		"""
		if site == "self"
			raise ValueError("must specify another site (not 'self'')")
		site = self.sites[site]
		return rssh(
			user=site.user,
			host=site.hosts[host_ref],
			proxy_user=site.proxy.get("user"),
			proxy_host=site.proxy.get("host"))

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
		src = os.path.join(self.sites["self"].paths[path_ref], path)
		dst = os.path.join(self.sites[site].paths[path_ref], path)
		if has_trailing_slash:
			src += "/"
			dst += "/"
		node = self.node(site, host_ref)
		return node.push(src=src, dst=dst, **kwargs)

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
		dst = os.path.join(self.sites["self"].paths[path_ref], path)
		if has_trailing_slash:
			src += "/"
			dst += "/"
		node = self.node(site, host_ref)
		return node.pull(src=src, dst=dst, **kwargs)

	def to_dict(self) -> dict[str: Any]:
		"""
		Format appropriately for serialization (to json)
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
		p = fix_path(p, must_exist=True)
		with open(p) as f:
			return cls.from_file(f)
