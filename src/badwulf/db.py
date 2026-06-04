
# Experiment data manager

import os
import shutil
import json
import tomllib

from collections.abc import Mapping
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import asdict
from dataclasses import fields
from operator import attrgetter
from datetime import datetime

from .tools import fix_path
from .tools import tree_find
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
	:ivar log: List of key-value entries of changes
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
		return grep(pattern, self.scope, ignore_case=True) is not None

	def has_group(self, pattern: str) -> bool:
		"""
		Detect if the dataset's group matches a pattern
		:param pattern: The group pattern
		:returns: True the expmeta has the group, False otherwise
		"""
		return grep(pattern, self.group, ignore_case=True) is not None

	def search(self, 
		pattern: str, 
		within: set[str] | None = None,
		ignore_case: bool = False,
		context_width: int = 60) -> expsearch | None:
		"""
		Search metadata for a regular expression
		:param pattern: The search pattern
		:param within: List of metadata fields to search; None means all
		:param ignore_case: Should case be ignored?
		:param context_width: Width of a context window for hits
		:returns: An expsearch object or None if no hits
		"""
		hits = {}
		d = asdict(self)
		for f in fields(self):
			if within is not None and f.name not in within:
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
		Format appropriately for serialization (to json, toml, etc.)
		:returns: A dict representation
		"""
		d = asdict(self)
		d = {k: v for k, v in d.items() if k != "name" and v is not None}
		return {self.name: rekey_snake_to_kebab(d)}

	@classmethod
	def from_dict(cls, d: dict[str: Any]):
		"""
		Create an expmeta from a dict
		:param d: A dict (parsed from json, toml, etc.)
		:returns: An expmeta object
		"""
		name = next(iter(d))
		d = rekey_kebab_to_snake(d[name])
		return cls(name=name, **d)

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
class expdata:
	"""
	Experimental metadata and file stats for a dataset
	:ivar path: The (real) path to the dataset directory
	:ivar _meta: Experimental metadata
	:ivar _meta_stat: File stats for metadata.toml
	:ivar _tree_stat: File stats for directory contents
	"""
	path: str
	_meta: expmeta | None = None
	_meta_stat: dict[str: int | float] | None = None
	_tree_stat: dict[str: int | float] | None = None

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
		Get experimental metadata
		"""
		if self._meta is None:
			with open(self.meta_path, "rb") as file:
				d = tomllib.load(file)
			self._meta = expmeta.from_dict(d)
		return self._meta

	@meta.setter
	def meta(self, value: expmeta) -> None:
		"""
		Set experimental metadata
		"""
		self._meta = value

	@property
	def meta_hash(self) -> int:
		"""
		Get a hash to compare if metadata has likely changed
		"""
		return hash((self.path, self.meta_mtime, self.meta_size))

	@property
	def meta_path(self) -> str:
		"""
		Get (real) metadata.toml path
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
	def atime(self) -> float:
		"""
		Get last accessed timestamp for the dataset directory contents
		"""
		return self._get_tree_stat()["atime"]

	@property
	def mtime(self) -> float:
		"""
		Get last modified timestamp for the dataset directory contents
		"""
		return self._get_tree_stat()["mtime"]

	@property
	def size(self) -> int:
		"""
		Get size of the dataset directory contents in bytes
		"""
		return self._get_tree_stat()["size"]

	@property
	def canonical_path(self) -> str:
		"""
		Get the (relative) canonical path (defined as scope/group/name)
		"""
		return os.path.join(self.meta.scope, self.meta.group, self.meta.name)

	def is_local(self) -> bool:
		"""
		Check if the dataset (including metadata.toml) exists locally
		"""
		return os.path.exists(self.meta_path)

	def is_misplaced_under(self, root: str) -> bool:
		"""
		Check if dataset is located at its canonical path under root
		"""
		expected = os.path.join(root, self.canonical_path)
		if os.path.exists(expected):
			return not os.path.samefile(expected, self.path)
		else:
			return True

	def place_under(self, root: str) -> None:
		"""
		Move the dataset to its canonical path under root
		"""
		self.move(os.path.join(root, self.canonical_path))

	def move(self, dst: str) -> None:
		"""
		Move the dataset to a new location
		"""
		if os.path.exists(dst):
			raise FileExistsError(f"move destination already exists: {dst}")
		else:
			shutil.move(self.path, dst)
		self.path = dst
		self._tree_stat = None
		self._get_meta_stat(True)

	def copy(self, dst: str) -> expdata:
		"""
		Copy the dataset to a new location and return the copy
		"""
		if os.path.exists(dst):
			raise FileExistsError(f"copy destination already exists: {dst}")
		else:
			shutil.copytree(self.path, dst)
		return expdata.from_path(dst)

	def sync(self, dst: str, con: rssh) -> None:
		"""
		Sync the dataset to another location over a connection
		"""
		pass

	def unlink(self) -> None:
		"""
		Delete the dataset directory and all its contents
		"""
		shutil.rmtree(self.path)
		self._meta = None
		self._meta_stat = None
		self._tree_stat = None

	def to_dict(self) -> dict[str: Any]:
		"""
		Format appropriately for serialization (to json, toml, etc.)
		:returns: A dict representation
		"""
		return {
			"path": self.path,
			"meta": self.meta.to_dict(),
			"meta_stat": self._get_meta_stat(),
			"tree_stat": self._get_tree_stat()}

	@classmethod
	def from_dict(cls, d: dict[str: Any]):
		"""
		Create an expmeta from a dict
		:param d: A dict (parsed from json, toml, etc.)
		:returns: An expdata object
		"""
		return cls(
			path=d["path"],
			_meta=expmeta.from_dict(d["meta"]),
			_meta_stat=d.get("meta_stat"),
			_tree_stat=d.get("tree_stat"))

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

class expindex(Mapping):
	"""
	Index of experimental datasets
	:ivar _index: Mapping of datasets by name
	"""
	_index: dict[str, expdata]

	def __init__(self, d: dict[str, expdata] | None = None):
		"""
		Create an expindex from a dict
		"""
		if d is None:
			self._index = {}
		else:
			self._index = d

	def __getitem__(self, key: str) -> expdata:
		"""
		Get an expdata item from the index
		"""
		return self._index[key]

	def __len__(self) -> int:
		"""
		Get the number of datasets in the index
		"""
		return len(self._index)

	def __iter__(self):
		"""
		Get an iterator over the database keys
		"""
		return iter(self._index)

	def filter(self, function: Callable[[expdata], bool]) -> expindex:
		"""
		Filter the datasets and return a new expindex
		:param function: A function returning True for expdata to keep
		:returns: A new expindex object (referencing original datasets)
		"""
		return expindex({k: v for k, v in self.items() if function(v)})

	def subset(self,
		names: set[str] | None = None,
		scope: set[str] | None = None,
		group: set[str] | None = None) -> expindex:
		"""
		Subset the datasets and return a new expindex
		:param names: A set of dataset names to keep
		:param scope: A set of scopes to keep
		:param group: A set of groups to keep
		:returns: A new expindex object (referencing original datasets)
		"""
		def subsetter(e):
			if names is not None:
				if e.meta.name not in names:
					return False
			if scope is not None:
				if not any(e.meta.has_scope(s) for s in scope):
					return False
			if group is not None:
				if not any(e.meta.has_group(g) for g in group):
					return False
			return True
		return self.filter(subsetter)

	def sorted(self,
		key: Callable[[expdata], Any],
		reverse: bool = False) -> list[expdata]:
		"""
		Return datasets in ascending sort order based on a key function
		:param key: A function taking an expdata returning a comparable key
		:param reverse: Sort in descending order?
		"""
		return sorted(self.values(), key=key, reverse=reverse)

	def sorted_by(self,
		*stats: str,
		reverse: bool = False) -> list[expdata]:
		"""
		Return datasets in ascending sort order by directory file stats
		:param stats: One or more of 'size', 'mtime', or 'atime'
		:param reverse: Sort in descending order?
		"""
		expected = ("atime", "mtime", "size")
		if stats is None or not all(st in expected for st in stats):
			raise ValueError(f"expected one or more of: {expected}")
		return self.sorted(key=attrgetter(*stats), reverse=reverse)

	def search(self, 
		pattern: str, 
		within: set[str] | None = None,
		ignore_case: bool = False,
		context_width: int = 60) -> dict[str, expsearch]:
		"""
		Search indexed metadata for a regular expression
		:param pattern: The search pattern
		:param within: List of metadata fields to search; None means all
		:param ignore_case: Should case be ignored?
		:param context_width: Width of a context window for hits
		:returns: A dict of expsearch objects with nonzero hits
		"""
		d = {}
		for k, v in self.items():
			hits = v.meta.search(pattern, within, ignore_case, context_width)
			if hits is not None:
				d[k] = hits
		return d

	@classmethod
	def from_list(cls, lst: list[expdata]):
		"""
		Create an expindex from a list
		:param lst: A list of expdata objects
		:returns: An expindex object:
		"""
		return cls({e.meta.name: e for e in lst})

	@classmethod
	def from_file(cls, f: io.TextIOBase | io.BufferedIOBase):
		"""
		Create an expindex from a json file
		:param f: An open json file
		:returns: A expindex object
		"""
		d = json.load(f)
		return cls({k: expdata.from_dict(v) for k, v in d.items()})

	@classmethod
	def from_path(cls, p: str):
		"""
		Create an expindex from a json file
		:param p: The path to a manifest.json file
		:returns: An expindex object
		"""
		p = fix_path(p, must_exist=True)
		with open(p) as f:
			return cls.from_file(f)

class expdb(Mapping):
	"""
	Database of experimental datasets
	:ivar root: The path to the database root
	:ivar datasets: List of datasets detected under root
	:ivar use_manifest: Read/write a manifest.json?
	:ivar _index: Mapping of datasets by name
	"""
	root: str
	datasets: list[expdata]
	use_manifest: bool = True
	_index: expindex | None = None

	def __init__(self, root: str, use_manifest = True):
		"""
		Create an expdb from a database directory
		:param root: The path to the root database directory
		:param use_manifest: Read/write a manifest.json?
		"""
		self.root = fix_path(root, must_exist=True)
		if not os.path.isdir(self.root):
			raise NotADirectoryError(f"root must be a directory: {self.root}")
		paths = tree_find(self.root, r"^metadata\.toml$", prune_on_match=True)
		self.datasets = [expdata.from_path(p) for p in paths]
		self.use_manifest = use_manifest
		self.ensure()

	def __getitem__(self, key: str) -> expdata | None:
		"""
		Get an expdata item from the database
		"""
		return self.index[key]

	def __len__(self) -> int:
		"""
		Get the number of datasets in the database
		"""
		return len(self.index)

	def __iter__(self):
		"""
		Get an iterator over the database keys
		"""
		return iter(self.index)

	@property
	def index(self) -> expindex:
		"""
		Get the database index
		"""
		if self._index is None:
			self.ensure()
		return self._index

	def ensure(self) -> None:
		"""
		Ensures the database is in a valid state
		"""
		if self.use_manifest and self.manifest_exists():
			self.refresh()
		else:
			self.rebuild()

	def rebuild(self) -> None:
		"""
		Rebuilds the database from the datasets alone
		"""
		self._index = expindex.from_list(self.datasets)
		if self.use_manifest:
			self.dump()

	def refresh(self) -> None:
		"""
		Refreshes the database from the datasets + manifest
		"""
		with open(self.manifest_path) as f:
			manifest = json.load(f)
		cache = {v.path: expdata.from_dict(v) for v in manifest.values()}
		db = {}
		num_changed = 0
		for e in self.datasets:
			c = cache.get(e.path)
			if c is None or e.meta_hash != c.meta_hash:
				num_changed += 1
			else:
				e.meta = c.meta
			db[e.meta.name] = e
		self._index = expindex(db)
		if num_changed > 0 and self.use_manifest:
			self.dump()

	def dump(self, 
		indent: int = 2, 
		sort_keys: bool = True) -> None:
		"""
		Dumps the database to manifest.json
		:param indent: Number of spaces to indent json
		:param sort_keys: Should the manifest be sorted?
		"""
		d = {k: v.to_dict() for k, v in self._index.items()}
		with open(self.manifest_path, "w") as f:
			json.dump(d, f, indent=indent, sort_keys=sort_keys)

	@property
	def manifest_path(self) -> str:
		"""
		Get path to the database manifest
		"""
		return os.path.join(self.root, "manifest.json")	

	def manifest_exists(self) -> bool:
		"""
		Checks if the database manifest exists
		"""
		return os.path.exists(self.manifest_path)

