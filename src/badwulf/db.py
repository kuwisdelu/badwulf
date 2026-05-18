
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

from .tools import fix_path
from .tools import dir_stat
from .tools import format_bytes
from .tools import grep1

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

@dataclass
class expdata:
	"""
	Experimental metadata and stats for a locally stored dataset
	"""
	path: str
	atime: float
	mtime: float
	size: int
	_meta: expmeta | None = None

	@property
	def atime_dt(self):
		"""
		Get last accessed timestamp
		"""
		return datetime.fromtimestamp(self.atime)

	@property
	def mtime_dt(self):
		"""
		Get last accessed timestamp
		"""
		return datetime.fromtimestamp(self.atime)

	@property
	def size_human(self):
		"""
		Get size in a human-readable string
		"""
		return format_bytes(self.size)

	@property
	def meta(self):
		"""
		Get experimental metadata
		"""
		if self._meta is None:
			with open(self.path, "rb") as file:
				d = tomllib.load(file)
			self._meta = expmeta.from_dict(d)
		return self._meta

	@classmethod
	def from_metadata(cls, path: str, all_files = False):
		"""
		Create an expdata from a toml file
		:param path: The path to the metadata.toml file
		:param all_files: Should the stats summarize the full directory?
		:returns: An expdata object
		"""
		path = fix_path(path, must_exist=True)
		if os.path.basename(path) != "metadata.toml":
			raise ValueError("path must be a 'metadata.toml' file")
		d = {"path": path}
		if all_files:
			d.update(dir_stat(path))
		else:
			st = os.stat(path)
			d.update({
				"atime": st.st_atime,
				"mtime": st.st_mtime,
				"size": st.st_size})
		return cls(**d)

