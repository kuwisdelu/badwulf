
# Synchronize projects and datasets

import os
import io
import json
from pathlib import Path
from dataclasses import dataclass
from dataclasses import asdict

from .tools import fix_path
from .tools import maybe_template

@dataclass
class profile:
	"""
	Profile information required for opening an SSH connection
	:ivar user: The profile username
	:ivar head: Default hostname/url for a login connection
	:ivar xfer: Optional hostname/url for a data transfer
	:ivar nodes: Optional node aliases-to-hostnames dict (if cluster)
	"""
	user: str | None
	head: str
	xfer: str | None = None
	nodes: dict[str, str] | None = None

@dataclass
class site:
	"""
	Site information for a cluster and/or server
	:ivar projpath: The path to the projects directory
	:ivar datapath: The path to the datasets directory
	:ivar cluster: Optional profile for a site cluster
	:ivar server: Optional profile for a site server
	"""
	prefix: str | None
	projpath: str | None
	datapath: str | None
	cluster: profile | None = None
	server: profile | None = None
	meta: dict[str, Any] | None = None

	def __post_init__(self):
		if self.prefix is None:
			if self.projpath is None and self.datapath is None:
				raise ValueError(
					"'projpath' and 'datapath' are required "
					"if 'prefix' is missing")
		else:
			if self.projpath is None:
				self.projpath = os.path.join(self.prefix, "Projects")
			if self.datapath is None:
				self.datapath = os.path.join(self.prefix, "Datasets")
		if self.cluster is not None:
			if self.cluster.nodes is None:
				raise ValueError("'cluster' must have 'nodes'")
			if self.cluster.xfer is None:
				raise ValueError("'cluster' must specify 'xfer' node")
		if self.projpath is not None and maybe_template(self.projpath):
			self.projpath = self.projpath.format(
				prefix=self.prefix, 
				cluster=self.cluster, 
				server=self.server)
		if self.datapath is not None and maybe_template(self.datapath):
			self.datapath = self.datapath.format(
				prefix=self.prefix, 
				cluster=self.cluster, 
				server=self.server)

	@classmethod
	def from_dict(cls, d: dict[str: Any]):
		"""
		Create a site from a dict 
		:param d: A dict (parsed from json)
		:returns: A site object
		"""
		cluster = profile(**d["cluster"]) if "cluster" in d else None
		server = profile(**d["server"]) if "server" in d else None
		return cls(
			prefix=d["prefix"],
			projpath=d.get("projpath"),
			datapath=d.get("datapath"),
			cluster=cluster,
			server=server,
			meta=d.get("meta"))

class syncer:
	"""
	Sync projects and datasets between sites
	"""

	def __init__(self, sites: dict[str, site]):
		"""
		Initializes a syncer instance
		:param sites: Mapping of aliases-to-sites
		"""
		if "local" not in sites:
			raise ValueError("required site 'local' is missing")
		if "origin" not in sites:
			raise ValueError("required site 'origin' is missing")
		if sites["local"].prefix is None:
			raise ValueError("'prefix' is required for site 'local'")
		self.sites = sites

	def to_dict(self) -> dict[str: site]:
		"""
		Convert to a dict representation
		:param d: A dictionary
		:returns: A syncer object
		"""
		return asdict(self.sites)

	@classmethod
	def from_dict(cls, d: dict[str, Any]):
		"""
		Create a syncer from a dict
		:param d: A dict (parsed from json)
		:returns: A syncer object
		"""
		return cls({k: site.from_dict(v) for k, v in d.items()})

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
