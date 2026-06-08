
# Synchronize files and directories across work sites

import os
import io
import json
from dataclasses import dataclass
from dataclasses import asdict

from .tools import fix_path
from .tools import prune

@dataclass
class profile:
	"""
	Profile information for a work site
	:ivar user: Username for work site authentication
	:ivar hosts: Dict of aliases-to-hostnames ('default': 'localhost', etc.)
	:ivar paths: Dict of aliases-to-paths ('default': '~/Projects', etc.)
	:ivar proxy: Dict of 'host' and 'user' for a jump proxy
	"""
	user: str | None = None
	hosts: dict[str, str | None] | None = None
	paths: dict[str, str | None] | None = None
	proxy: dict[str, str | None] | None = None

class syncer:
	"""
	Sync projects and datasets between sites
	"""

	def __init__(self, sites: dict[str, profile]):
		"""
		Initializes a syncer instance
		:param sites: Mapping of aliases-to-sites
		"""
		if "self" not in sites:
			raise ValueError("missing required site 'self'")
		self.sites = sites

	def push(self, 
		src: str,
		dst: str,
		site_ref: str | None = None,
		host_ref: str | None = None,
		path_ref: str | None = None,
		mirror: bool = False,
		dry_run: bool = False,
		ask: bool = False) -> None:
		"""
		Push a file or directory to another site (via rsync)
		:param src: The source path (on self)
		:param dst: The destination path (on site_ref:host_ref)
		:param site_ref: The other site name (optional)
		:param host_ref: The other site host (optional)
		:param path_ref: The anchor path alias (optional)
		:param mirror: Delete files in dst that aren't in src?
		:param dry_run: Show what would be done without doing it?
		:param ask: Confirm before pushing?
		"""
		pass

	def pull(self, 
		src: str,
		dst: str,
		site_ref: str | None = None,
		host_ref: str | None = None,
		path_ref: str | None = None,
		mirror: bool = False,
		dry_run: bool = False,
		ask: bool = False) -> None:
		"""
		Pull a file or directory from another site (via rsync)
		:param src: The source path (on site_ref:host_ref)
		:param dst: The destination path (on self)
		:param site_ref: The other site name (optional)
		:param host_ref: The other site host (optional)
		:param path_ref: The anchor path alias (optional)
		:param mirror: Delete files in dst that aren't in src?
		:param dry_run: Print to stdout what would be done without doing it?
		:param ask: Confirm before pulling?
		"""
		pass

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
