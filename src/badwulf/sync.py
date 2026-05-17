
# Synchronize projects and datasets

import json
from dataclasses import asdict

from .sites import site
from .tools import fix_path

class syncer:
	"""
	Sync projects and datasets between sites
	"""

	def __init__(self, sites: dict[str, site]):
		"""
		Initializes a syncer instance
		:param sites: Dictionary of aliases-to-sites
		"""
		if "local" not in sites:
			raise ValueError("required site 'local' is missing")
		if "origin" not in sites:
			raise ValueError("required site 'origin' is missing")
		if sites["local"].prefix is None:
			raise ValueError("'prefix' is required for site 'local'")
		self.sites = sites

	def to_dict(self):
		"""
		Create a syncer from a dict (usually parsed from json)
		:param d: A dictionary
		:returns: A syncer object
		"""
		return asdict(self.sites)

	@classmethod
	def from_dict(cls, d):
		"""
		Create a syncer from a dict (usually parsed from json)
		:param d: A dictionary
		:returns: A syncer object
		"""
		return cls({k: site.from_dict(v) for k, v in d.items()})

	@classmethod
	def from_config(cls, path):
		"""
		Create a syncer from a json file
		:param path: The path of the configuration file
		:returns: A syncer object
		"""
		path = fix_path(path, must_exist=True)
		with open(path) as file:
			d = json.load(file)
		return cls.from_dict(d)
