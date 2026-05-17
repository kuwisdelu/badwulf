
# Server user and hostname/url information

import os
from dataclasses import dataclass
from .tools import is_template

@dataclass
class profile:
	"""
	Profile information required for opening a connection
	:ivar user: The profile username; ask user interactively if None
	:ivar head: Default hostname/url for a login connection
	:ivar xfer: Optional hostname/url for a data transfer
	:ivar nodes: Optional nodealiases-to-hostnames dict if a cluster
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
	meta: dict[str, str] | None = None

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
		if self.projpath is not None and is_template(self.projpath):
			self.projpath = self.projpath.format(
				prefix=self.prefix, 
				cluster=self.cluster, 
				server=self.server)
		if self.datapath is not None and is_template(self.datapath):
			self.datapath = self.datapath.format(
				prefix=self.prefix, 
				cluster=self.cluster, 
				server=self.server)

	@classmethod
	def from_dict(cls, d):
		"""
		Create a site from a dict (usually parsed from json)
		:param d: A dictionary
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

