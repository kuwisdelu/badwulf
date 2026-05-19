
# Synchronize projects and datasets

import json
import io
from pathlib import Path
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

	def to_dict(self) -> dict:
		"""
		Create a syncer from a dict (usually parsed from json)
		:param d: A dictionary
		:returns: A syncer object
		"""
		return asdict(self.sites)

	@classmethod
	def from_dict(cls, d: dict):
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
