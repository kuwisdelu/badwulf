
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
from dataclasses import fields
from datetime import datetime

from .tools import fix_path
from .tools import dir_stat
from .tools import grep
from .tools import prune_none

@dataclass
class expmeta:
	"""
	Experimental metadata for a scientific dataset
	:ivar name: The dataset identifier
	:ivar title: A short title for the dataset
	:ivar group: The research group or data repository
	:ivar scope: The scoping for how the data can be used
	:ivar description: A long description of the experiment
	:ivar sample_processing: Sample preparation and protocols
	:ivar data_processing: Data processing and analysis
	:ivar contact: List of entries for people responsible
	:ivar url: Key-values of relevant URLs (publications, repositories, etc.)
	:ivar date: Key-values of relevant dates (created, received, etc.)
	:ivar formats: List of relevant file formats in the dataset
	:ivar keywords: List of keywords for the dataset/experiment
	:ivar note: List of free form notes
	"""
	name: str
	title: str
	group: str
	scope: str
	description: str | None = None
	sample_processing: str | None = None
	data_processing: str | None = None
	contact: list[dict[str, str]] | None = None
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
		return grep(pattern, self.scope) is not None

	def has_group(self, pattern: str) -> bool:
		"""
		Detect if the dataset's group matches a pattern
		:param pattern: The group pattern
		:returns: True the expmeta has the group, False otherwise
		"""
		return grep(pattern, self.group) is not None

	def search(self, 
		pattern: str, 
		where: set[str] | None = None,
		ignore_case: bool = True,
		context_width: int = 60) -> expsearch | None:
		"""
		Search metadata for a regular expression
		:param pattern: The search pattern
		:param where: List of metadata fields to search; None means all
		:param ignore_case: Should case be ignored?
		:param context_width: Width of a context window for hits
		:returns: An expsearch object or None if no hits
		"""
		hits = {}
		d = asdict(self)
		for f in fields(self):
			if where is not None and f.name not in where:
				continue
			v = d[f.name]
			matches = grep(pattern, v, ignore_case, context_width)
			if isinstance(matches, (list, dict)):
				matches = prune_none(matches)
				if len(matches) == 0:
					matches = None
			if matches is not None:
				hits[f.name] = matches
		if len(hits) > 0:
			return expsearch(
				name=self.name,
				title=self.title,
				group=self.group,
				scope=self.scope,
				pattern=pattern,
				hits=hits)
		else:
			return None

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
	Experimental metadata and file stats for a local dataset
	:ivar path: The path to the metadata.toml file
	:ivar atime: Last access time for the metadata/dataset
	:ivar atime: Last modified time for the metadata/dataset
	:ivar size: Size of the metadata/dataset
	:ivar all_files: Do the stats refer to all files or metadata only?
	:ivar _meta: The experimental metadata (parsed lazily)
	"""
	path: str
	atime: float
	mtime: float
	size: int
	all_files: bool = False
	_meta: expmeta | None = None

	@property
	def atime_dt(self) -> datetime:
		"""
		Get last accessed timestamp
		"""
		return datetime.fromtimestamp(self.atime)

	@property
	def mtime_dt(self) -> datetime:
		"""
		Get last accessed timestamp
		"""
		return datetime.fromtimestamp(self.atime)

	@property
	def meta(self) -> expmeta:
		"""
		Get experimental metadata as an expmeta object
		"""
		if self._meta is None:
			with open(self.path, "rb") as file:
				d = tomllib.load(file)
			self._meta = expmeta.from_dict(d)
		return self._meta

	@classmethod
	def from_path(cls, p: str, all_files: bool = False):
		"""
		Create an expdata from a toml file
		:param p: The path to the metadata.toml file
		:param all_files: Get stats for full dataset not just metadata.toml?
		:returns: An expdata object
		"""
		p = fix_path(p, must_exist=True)
		if os.path.basename(p) != "metadata.toml":
			raise ValueError("path must be a 'metadata.toml' file")
		d = {"path": p, "all_files": all_files}
		if all_files:
			d.update(dir_stat(p))
		else:
			st = os.stat(p)
			d.update({
				"atime": st.st_atime,
				"mtime": st.st_mtime,
				"size": st.st_size})
		return cls(**d)

@dataclass
class expsearch:
	"""
	Experimental metadata search hits
	:ivar name: The dataset identifier
	:ivar title: A short title for the dataset
	:ivar group: The research group or data repository
	:ivar scope: The scoping for how the data can be used
	:ivar pattern: The search pattern
	:ivar hits: Mapping of search hits
	"""
	name: str
	title: str
	group: str
	scope: str
	pattern: str
	hits: dict[str: list[Any]] | None = None

