
# Experiment data manager

import os
import shutil
import json
import tomllib
import datetime

from collections.abc import Collection
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import MutableMapping
from dataclasses import dataclass
from dataclasses import asdict
from dataclasses import fields
from operator import attrgetter

from .util import mkpath
from .util import tree_find
from .util import tree_stat
from .util import grep
from .util import prune

@dataclass
class projmeta:
	"""
	Project metadata for scientific research artifacts
	:ivar name: The project identifier
	:ivar scope: The scoping for how the project can be used
	:ivar group: The grouping for the org or repository
	:ivar title: A short title for the project
	:ivar date: Key-values of important dates (created, updated, etc.)
	:ivar refs: List of related project identifiers
	:ivar keywords: List of keywords and subject areas for the project
	:ivar formats: List of file formats and resource types in the project
	:ivar contact: List of key-value entries for people/orgs responsible
	:ivar description: Key-values of descriptions (abtract, methods, etc.)
	:ivar reference: Key-values of references (doi, url, etc.)
	"""
	name: str
	scope: str
	group: str
	title: str | None = None
	date: dict[str, datetime.date] | None = None
	keywords: list[str] | None = None
	formats: list[str] | None = None
	contact: list[dict[str, str]] | None = None
	description: dict[str, str] | None = None
	reference: dict[str, str] | None = None

	def has_name(self, pattern: str) -> bool:
		"""
		Detect if the project's name matches a pattern
		:param pattern: The name pattern
		:returns: True if projmeta has the name, False otherwise
		"""
		return grep(pattern, self.name, ignore_case=True) is not None

	def has_scope(self, pattern: str) -> bool:
		"""
		Detect if the project's scope matches a pattern
		:param pattern: The scope pattern
		:returns: True if projmeta has the scope, False otherwise
		"""
		return grep(pattern, self.scope, ignore_case=True) is not None

	def has_group(self, pattern: str) -> bool:
		"""
		Detect if the project's group matches a pattern
		:param pattern: The group pattern
		:returns: True if projmeta has the group, False otherwise
		"""
		return grep(pattern, self.group, ignore_case=True) is not None

	def search(self, 
		pattern: str, 
		within: Collection[str] | None = None,
		ignore_case: bool = False,
		context_width: int = 60) -> projsearch | None:
		"""
		Search metadata for a regular expression
		:param pattern: The search pattern
		:param within: List of metadata fields to search; None means all
		:param ignore_case: Should case be ignored?
		:param context_width: Width of a context window for hits
		:returns: An projsearch object or None if no hits
		"""
		hits = {}
		for k, v in self.to_dict().items():
			if within is not None and k not in within:
				continue
			matches = grep(pattern, v, ignore_case, context_width)
			if isinstance(matches, (list, dict)):
				matches = prune(matches)
				if len(matches) == 0:
					matches = None
			if matches is not None:
				hits[k] = matches
		if len(hits) > 0:
			return projsearch(
				name=self.name,
				scope=self.scope,
				group=self.group,
				pattern=pattern,
				hits=hits)
		else:
			return None

	def to_dict(self) -> dict[str, Any]:
		"""
		Format safely for serialization (to json, toml, etc.)
		:returns: A dict representation
		"""
		d = asdict(self)
		if d.get("date") is not None:
			d["date"] = {k: str(v) for k, v in d["date"].items()}
		return prune(d)

	@classmethod
	def from_dict(cls, d: dict[str, Any]):
		"""
		Create a projmeta from a dict
		:param d: A dict (parsed from json, toml, etc.)
		:returns: A projdata object
		"""
		d = prune(d)
		def iso(x):
			if isinstance(x, str):
				return datetime.date.fromisoformat(x)
			else:
				return x
		if d.get("date") is not None:
			d["date"] = {k: iso(v) for k, v in d["date"].items()}
		return cls(**d)

@dataclass
class projsearch:
	"""
	Project metadata search hits
	:ivar name: The project identifier
	:ivar scope: The scoping for how the project can be used
	:ivar group: The grouping for the org or repository
	:ivar pattern: The search pattern
	:ivar hits: Mapping of search hits
	"""
	name: str
	scope: str
	group: str
	pattern: str
	hits: dict[str, str | list[Any]] | None = None

@dataclass
class projdata:
	"""
	Project metadata and file stats for its contents
	:ivar path: The (real) path to the project directory
	:ivar _meta: Project metadata
	:ivar _meta_stat: File stats for project metadata.toml
	:ivar _tree_stat: File stats for project directory
	"""
	path: str
	_meta: projmeta | None = None
	_meta_stat: dict[str, int | float] | None = None
	_tree_stat: dict[str, int | float] | None = None

	def _fetch_meta_stat(self, force = False) -> dict[str, int | float]:
		"""
		Get stats for project metadata.toml
		"""
		if self._meta_stat is None or force:
			st = os.stat(self.meta_path)
			self._meta_stat = {
				"atime": st.st_atime,
				"mtime": st.st_mtime,
				"size": st.st_size}
		return self._meta_stat

	def _fetch_tree_stat(self, force = False) -> dict[str, int | float]:
		"""
		Get stats for project directory
		"""
		if self._tree_stat is None or force:
			self._tree_stat = tree_stat(self.path, 
				time_exclude={"metadata.toml"})
		return self._tree_stat

	@property
	def meta(self) -> projmeta:
		"""
		Get project metadata
		"""
		if self._meta is None:
			with open(self.meta_path, "rb") as file:
				d = tomllib.load(file)
			self._meta = projmeta(**d)
		return self._meta

	@meta.setter
	def meta(self, value: projmeta) -> None:
		"""
		Set project metadata
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
		return self._fetch_meta_stat()["atime"]

	@property
	def meta_mtime(self) -> float:
		"""
		Get last modified timestamp for metadata.toml
		"""
		return self._fetch_meta_stat()["mtime"]

	@property
	def meta_size(self) -> int:
		"""
		Get size of metadata.toml
		"""
		return self._fetch_meta_stat()["size"]

	@property
	def atime(self) -> float:
		"""
		Get last accessed timestamp for the dataset directory contents
		"""
		return self._fetch_tree_stat()["atime"]

	@property
	def mtime(self) -> float:
		"""
		Get last modified timestamp for the dataset directory contents
		"""
		return self._fetch_tree_stat()["mtime"]

	@property
	def size(self) -> int:
		"""
		Get size of the dataset directory contents in bytes
		"""
		return self._fetch_tree_stat()["size"]

	@property
	def name(self) -> str:
		"""
		Get the name of the project
		"""
		return self.meta.name

	@property
	def canonical_path(self) -> str:
		"""
		Get the (relative) canonical path (defined as scope/group/name)
		"""
		return os.path.join(
			self.meta.scope.casefold(), 
			self.meta.group.casefold(), 
			self.meta.name)

	def is_local(self) -> bool:
		"""
		Check if the project (including metadata.toml) exists locally
		"""
		return os.path.exists(self.meta_path)

	def is_misplaced_relative(self, root: str) -> bool:
		"""
		Check if project is located at its canonical path under root
		"""
		expected = os.path.join(root, self.canonical_path)
		if os.path.exists(expected):
			return not os.path.samefile(expected, self.path)
		else:
			return True

	def place_relative(self, root: str) -> None:
		"""
		Move the project to its canonical path under root
		"""
		self.move(os.path.join(root, self.canonical_path))

	def move(self, dst: str) -> None:
		"""
		Move the project to a new location
		"""
		if os.path.exists(dst):
			raise FileExistsError(f"move destination already exists: {dst}")
		else:
			shutil.move(self.path, dst)
		self.path = dst
		self._tree_stat = None
		self._fetch_meta_stat(True)

	def copy(self, dst: str) -> projdata:
		"""
		Copy the project to a new location and return the copy
		"""
		if os.path.exists(dst):
			raise FileExistsError(f"copy destination already exists: {dst}")
		else:
			shutil.copytree(self.path, dst)
		return projdata.from_path(dst)

	def unlink(self) -> None:
		"""
		Delete the project directory and all its contents
		"""
		shutil.rmtree(self.path)
		self._meta = None
		self._meta_stat = None
		self._tree_stat = None

	def to_dict(self) -> dict[str: Any]:
		"""
		Format safely for serialization (to json, toml, etc.)
		:returns: A dict representation
		"""
		return {
			"path": self.path,
			"meta": self.meta.to_dict(),
			"meta_stat": self._fetch_meta_stat(),
			"tree_stat": self._fetch_tree_stat()}

	@classmethod
	def from_dict(cls, d: dict[str: Any]):
		"""
		Create a projdata from a dict
		:param d: A dict (parsed from json, toml, etc.)
		:returns: A projdata object
		"""
		return cls(
			path=d["path"],
			_meta=projmeta.from_dict(d["meta"]),
			_meta_stat=d.get("meta_stat"),
			_tree_stat=d.get("tree_stat"))

	@classmethod
	def from_path(cls, p: str):
		"""
		Create a projdata from a file path or directory
		:param p: The path to a directory or a metadata.toml file
		:returns: A projdata object
		"""
		p = mkpath(p, must_exist=True)
		if not os.path.isdir(p):
			p = os.path.dirname(p)
		return cls(path=p)

class projindex(MutableMapping):
	"""
	Index of scientific research projects and metadata
	:ivar _index: Mapping of projects by name (case-insensitive)
	"""
	_index: dict[str, projdata]

	def __init__(self, d: dict[str, projdata] | None = None):
		"""
		Create an projindex from a dict
		"""
		if d is None:
			self._index = {}
		else:
			self._index = d

	def __getitem__(self, key: str) -> projdata:
		"""
		Get a projdata item in the index
		"""
		return self._index[key.casefold()]

	def __setitem__(self, key: str, value: projdata) -> None:
		"""
		Set a projdata item in the index
		"""
		self._index[key.casefold()] = value

	def __delitem__(self, key: str) -> None:
		"""
		Delete a projdata item in the index
		"""
		del self._index[key.casefold()]

	def __len__(self) -> int:
		"""
		Get the number of projects in the index
		"""
		return len(self._index)

	def __iter__(self):
		"""
		Get an iterator over the database keys
		"""
		return iter(self._index)

	def filter(self, function: Callable[[projdata], bool]) -> projindex:
		"""
		Filter the projects and return a new projindex
		:param function: A function returning True for projdata to keep
		:returns: A new projindex object (referencing original projects)
		"""
		return projindex({k: v for k, v in self.items() if function(v)})

	def subset(self,
		names: Collection[str] | None = None,
		scope: Collection[str] | None = None,
		group: Collection[str] | None = None) -> projindex:
		"""
		Subset the projects and return a new projindex
		:param names: A set of project names to keep
		:param scope: A set of scopes to keep
		:param group: A set of groups to keep
		:returns: A new projindex object (referencing original projects)
		"""
		if isinstance(names, str):
			names = [names]
		if isinstance(scope, str):
			scope = [scope]
		if isinstance(group, str):
			group = [group]
		def subsetter(proj):
			if names is not None:
				if not any(proj.meta.has_name(nm) for nm in names):
					return False
			if scope is not None:
				if not any(proj.meta.has_scope(s) for s in scope):
					return False
			if group is not None:
				if not any(proj.meta.has_group(g) for g in group):
					return False
			return True
		return self.filter(subsetter)

	def sorted(self,
		key: Callable[[projdata], Any],
		reverse: bool = False) -> list[projdata]:
		"""
		Return projects in ascending sort order based on a key function
		:param key: A function taking a projdata returning a comparable key
		:param reverse: Sort in descending order?
		:returns: A list of sorted projdata objects
		"""
		return sorted(self.values(), key=key, reverse=reverse)

	def sorted_by(self,
		*stats: str,
		reverse: bool = False) -> list[projdata]:
		"""
		Return projects in ascending sort order by directory file stats
		:param stats: One or more of 'name', 'size', 'mtime', or 'atime'
		:param reverse: Sort in descending order?
		:returns: A list of sorted projdata objects
		"""
		expected = ("name", "size", "mtime", "atime")
		if stats is None or not all(st in expected for st in stats):
			raise ValueError(f"expected one or more of: {expected}")
		return self.sorted(key=attrgetter(*stats), reverse=reverse)

	def search(self, 
		pattern: str, 
		within: Collection[str] | None = None,
		ignore_case: bool = False,
		context_width: int = 60,
		sorted_by: Collection[str] | None = None,
		reverse: bool = False) -> list[projsearch]:
		"""
		Search indexed metadata for a regular expression
		:param pattern: The search pattern
		:param within: List of metadata fields to search; None means all
		:param ignore_case: Should case be ignored?
		:param context_width: Width of a context window for hits
		:returns: A list of projsearch objects with nonzero hits
		"""
		hits = []
		if sorted_by is None:
			projects = self.sorted_by("name", reverse=reverse)
		else:
			projects = self.sorted_by(*sorted_by, reverse=reverse)
		for proj in projects:
			hit = proj.meta.search(pattern, within, ignore_case, context_width)
			if hit is not None:
				hits.append(hit)
		return hits

	@classmethod
	def from_list(cls, lst: list[projdata]):
		"""
		Create an projindex from a list
		:param lst: A list of projdata objects
		:returns: An projindex object:
		"""
		return cls({proj.meta.name.casefold(): proj for proj in lst})

	@classmethod
	def from_file(cls, f: io.TextIOBase | io.BufferedIOBase):
		"""
		Create an projindex from a json file
		:param f: An open json file
		:returns: A projindex object
		"""
		lst = [projdata.from_dict(d) for d in json.load(f)]
		return cls.from_list(lst)

	@classmethod
	def from_path(cls, p: str):
		"""
		Create an projindex from a json file
		:param p: The path to a manifest.json file
		:returns: An projindex object
		"""
		p = mkpath(p, must_exist=True)
		with open(p) as f:
			return cls.from_file(f)

class projdb(Mapping):
	"""
	Database of scientific research projects
	:ivar root: The path to the database root
	:ivar projects: List of projects detected under root
	:ivar use_manifest: Read/write a manifest.json?
	:ivar _index: Mapping of projects by name (case-insensitive)
	"""
	root: str
	projects: list[projdata]
	use_manifest: bool = True
	_index: projindex | None = None

	def __init__(self, root: str, use_manifest = True):
		"""
		Create an projdb from a database directory
		:param root: The path to the database root
		:param use_manifest: Read/write a manifest.json?
		"""
		self.root = mkpath(root, must_exist=True)
		if not os.path.isdir(self.root):
			raise NotADirectoryError(f"root must be a directory: {self.root}")
		paths = tree_find(self.root, r"^metadata\.toml$", prune_on_match=True)
		self.projects = [projdata.from_path(p) for p in paths]
		self.use_manifest = use_manifest
		self.ensure()

	def __getitem__(self, key: str) -> projdata | None:
		"""
		Get a projdata item from the database
		"""
		return self.index[key]

	def __len__(self) -> int:
		"""
		Get the number of projects in the database
		"""
		return len(self.index)

	def __iter__(self):
		"""
		Get an iterator over the database keys
		"""
		return iter(self.index)

	@property
	def index(self) -> projindex:
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
		Rebuilds the database from the projects alone
		"""
		self._index = projindex.from_list(self.projects)
		if self.use_manifest:
			self.dump()

	def refresh(self) -> None:
		"""
		Refreshes the database from the projects + manifest
		"""
		with open(self.manifest_path) as f:
			lst = json.load(f)
		manifest = {proj["path"]: projdata.from_dict(proj) for proj in lst}
		index = projindex()
		num_cache_miss = 0
		for proj in self.projects:
			cached = manifest.get(proj.path)
			if cached is None or proj.meta_hash != cached.meta_hash:
				num_cache_miss += 1
			else:
				proj.meta = cached.meta
			index[proj.meta.name] = proj
		self._index = index
		if num_cache_miss > 0 and self.use_manifest:
			self.dump()

	def dump(self, indent: int = "\t") -> None:
		"""
		Dumps the database to manifest.json
		:param indent: Number of spaces to indent json
		"""
		lst = [proj.to_dict() for proj in self.projects]
		with open(self.manifest_path, "w") as f:
			json.dump(lst, f, indent=indent)

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
