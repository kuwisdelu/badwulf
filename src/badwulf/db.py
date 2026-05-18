
# Experiment data manager

import os
import sys
if sys.version_info >= (3, 11):
	import tomllib
else:
	import tomli as tomllib

import shutil
from dataclasses import dataclass
from dataclasses import asdict
from datetime import datetime

from .rssh import rssh
from .tools import ls
from .tools import fix_path
from .tools import dir_stat
from .tools import dir_find
from .tools import to_bytes
from .tools import confirm
from .tools import grep1
from .tools import grepl

@dataclass
class expmeta:
	"""
	Experimental metadata for a scientific dataset
	"""
	name: str
	title: str
	group: str
	scope: str
	description: str | None = None
	sample_processing: str | None = None
	data_processing: str | None = None
	contact: dict[str, str] | None = None
	url: dict[str, str] | None = None
	date: dict[str, str] | None = None
	formats: list[str] | None = None
	keywords: list[str] | None = None
	notes: list[str] | None = None
	
	def __str__(self):
		"""
		Return str(self)
		"""
		return self.describe(self.printwidth)

	def has_scope(self, pattern: str) -> bool:
		"""
		Detect if the dataset's scope matches a pattern
		:param pattern: The scope pattern
		:returns: True the expmeta has the scope, False otherwise
		"""
		return grep1(pattern, self.scope) is not None

	def has_group(self, pattern: str) -> bool:
		"""
		Detect if the dataset's group matches a pattern
		:param pattern: The group pattern
		:returns: True the expmeta has the group, False otherwise
		"""
		return grep1(pattern, self.group) is not None

	def to_dict(self) -> dict:
		"""
		Format appropriately for writing json or toml
		:returns: A dict representation
		"""
		d = asdict(self)
		d = {k: v for k, v in d.items() if k != "name" and v is not None}
		return {self.name: d}

	@classmethod
	def from_dict(cls, d: dict):
		"""
		Create an expmeta from a dict
		:param d: A dict (parsed from json or toml)
		:returns: An expmeta object
		"""
		name = next(iter(d))
		return cls(name=name, **d[name])

	@classmethod
	def from_metadata(cls, path: str):
		"""
		Create an expmeta from a toml file
		:param path: The path to the metadata.toml file
		:returns: An expmeta object
		"""
		with open(path, "rb") as file:
			d = tomllib.load(file)
		return cls.from_dict(d)
