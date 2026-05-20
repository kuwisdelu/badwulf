
# Experiment data manager

import os
import sys
if sys.version_info >= (3, 11):
	import tomllib
else:
	import tomli as tomllib

from dataclasses import dataclass
from dataclasses import asdict
from dataclasses import fields
from datetime import datetime

from .tools import fix_path
from .tools import tree_stat
from .tools import grep
from .tools import prune
from .tools import rekey_kebab_to_snake
from .tools import rekey_snake_to_kebab

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
	:ivar contact: List of key-value entries for people/orgs responsible
	:ivar log: List of key-value entries of changes (by version or date)
	:ivar url: Key-values of URLs (doi, publications, repositories, etc.)
	:ivar date: Key-values of events (created, received, etc.)
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
	log: list[dict[str, str]] | None = None
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
				matches = prune(matches)
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

	def to_dict(self) -> dict[str: Any]:
		"""
		Format appropriately for serialization (to json or toml)
		:returns: A dict representation
		"""
		d = asdict(self)
		d = {k: v for k, v in d.items() if k != "name" and v is not None}
		return {self.name: rekey_snake_to_kebab(d)}

	@classmethod
	def from_dict(cls, d: dict[str: Any]):
		"""
		Create an expmeta from a dict
		:param d: A dict (parsed from json or toml)
		:returns: An expmeta object
		"""
		name = next(iter(d))
		d = rekey_kebab_to_snake(d[name])
		return cls(name=name, **d)

@dataclass
class expdata:
	"""
	Experimental metadata and file stats for a local dataset
	:ivar path: The path to the metadata.toml file
	:ivar _meta: Experimental metadata
	:ivar _meta_stat: File stats for metadata.toml
	:ivar _tree_stat: File stats for directory contents
	"""
	path: str
	_meta: expmeta | None = None
	_meta_stat: dict[str: int | float] | None = None
	_tree_stat: dict[str: int | float] | None = None

	def __post_init__(self):
		fp = self.meta_path
		if not os.path.exists(fp):
			raise ValueError(f"missing metadata file: {fp}")
		self._get_meta_stat(True)

	def _get_meta(self, force = False) -> expmeta:
		"""
		Get experimental metadata
		"""
		if self._meta is None or force:
			with open(self.meta_path, "rb") as file:
				d = tomllib.load(file)
			self._meta = expmeta.from_dict(d)
		return self._meta

	def _get_meta_stat(self, force = False) -> dict[str: int | float]:
		"""
		Get stats for metadata.toml
		"""
		if self._meta_stat is None or force:
			st = os.stat(self.meta_path)
			self._meta_stat = {
				"atime": st.st_atime,
				"mtime": st.st_mtime,
				"size": st.st_size}
		return self._meta_stat

	def _get_tree_stat(self, force = False) -> dict[str: int | float]:
		"""
		Get stats for directory contents
		"""
		if self._tree_stat is None or force:
			self._tree_stat = tree_stat(self.path, 
				time_exclude={"metadata.toml"})
		return self._tree_stat

	@property
	def meta(self) -> expmeta:
		"""
		Get experimental metadata as an expmeta object
		"""
		return self._get_meta()

	@property
	def meta_path(self) -> str:
		"""
		Get metadata.toml path
		"""
		return os.path.join(self.path, "metadata.toml")

	@property
	def meta_atime(self) -> float:
		"""
		Get last accessed timestamp for metadata.toml
		"""
		return self._get_meta_stat()["atime"]

	@property
	def meta_mtime(self) -> float:
		"""
		Get last modified timestamp for metadata.toml
		"""
		return self._get_meta_stat()["mtime"]

	@property
	def meta_size(self) -> int:
		"""
		Get size of metadata.toml
		"""
		return self._get_meta_stat()["size"]

	@property
	def tree_atime(self) -> float:
		"""
		Get last accessed timestamp for the directory contents
		"""
		return self._get_tree_stat()["atime"]

	@property
	def tree_mtime(self) -> float:
		"""
		Get last modified timestamp for the directory contents
		"""
		return self._get_tree_stat()["mtime"]

	@property
	def tree_size(self) -> int:
		"""
		Get size of the directory contents in bytes
		"""
		return self._get_tree_stat()["size"]

	def move(self, path: str) -> None:
		"""
		Move the dataset to a new location
		"""
		pass

	def copy(self, path: str) -> expdata:
		"""
		Copy the dataset to a new location and return the copy
		"""
		pass

	def sync(self, dest: str, con: rssh) -> None:
		"""
		Sync the dataset to another location over a connection
		"""
		pass

	def unlink(self) -> None:
		"""
		Delete the dataset directory and all its contents
		"""
		pass

	def to_dict(self) -> dict:
		"""
		Format appropriately for serialization (to json or toml)
		:returns: A dict representation
		"""
		return {
			"path": self.path,
			"meta": self.meta.to_dict(),
			"meta_stat": self._get_meta_stat(),
			"tree_stat": self._get_tree_stat()}

	@classmethod
	def from_path(cls, p: str):
		"""
		Create an expdata from a file path or directory
		:param p: The path to a directory or a metadata.toml file
		:returns: An expdata object
		"""
		p = fix_path(p, must_exist=True)
		if not os.path.isdir(p):
			p = os.path.dirname(p)
		return cls(path=p)

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

@dataclass
class expdb:
	"""
	Database of experimental datasets
	:ivar manifest: The manifest of tracked datasets and metadata
	:ivar datasets: The collection of locally stored datasets
	"""
	manifest: dict[str, expmeta] | None = None
	datasets: dict[str, expdata] | None = None

	@classmethod
	def from_path(cls, p: str):
		"""
		Create an expdb from a file path or directory
		:param p: The path to directory or a manifest file
		:returns: An expdb object
		"""
		pass

	@classmethod
	def from_dir(cls, p: str):
		"""
		Create an expdb from a directory of datasets
		:param p: A directory path to walk to find metadata.toml files
		:returns: An expdb object
		"""
		pass

	@classmethod
	def from_file(cls, f: io.TextIOBase | io.BufferedIOBase):
		"""
		Create an expdb from a json file
		:param f: An open json file
		:returns: An expdb object
		"""
		pass

