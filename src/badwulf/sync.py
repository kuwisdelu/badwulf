
# Synchronize projects and datasets

import json
from dataclasses import dataclass
from .sites import site
from .rssh import rssh
from .tools import fix_path

@dataclass
class syncer:
	"""
	Sync projects and datasets between sites
	:ivar sites: Dictionary of aliases-to-sites
	"""
	sites: dict[str, site]

	@classmethod
	def from_config(cls, path):
		"""
		Create a syncer from a json file
		:param path: The path of the configuration file
		:returns: A syncer object
		"""
		path = fix_path(path, must_exist=True)
		with open(path) as file:
			p = json.load(file)
		return cls({k: site(**v) for k, v in p.items()})
