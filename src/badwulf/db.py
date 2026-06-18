
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
from dataclasses import field
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
			self._meta_stat = {"size": st.st_size, "mtime": st.st_mtime}
		return self._meta_stat

	def _fetch_tree_stat(self, force = False) -> dict[str, int | float]:
		"""
		Get stats for project directory
		"""
		if self._tree_stat is None or force:
			self._tree_stat = tree_stat(self.path)
		return self._tree_stat

	@property
	def name(self) -> str:
		"""
		Get the name of the project
		"""
		return self.meta.name

	@property
	def size(self) -> int:
		"""
		Get size of the dataset directory contents in bytes
		"""
		return self._fetch_tree_stat()["size"]

	@property
	def mtime(self) -> float:
		"""
		Get last modified timestamp for the dataset directory contents
		"""
		return self._fetch_tree_stat()["mtime"]

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
		return hash((self.path, self.meta_size, self.meta_mtime))

	@property
	def meta_path(self) -> str:
		"""
		Get (real) metadata.toml path
		"""
		return os.path.join(self.path, "metadata.toml")

	@property
	def meta_size(self) -> int:
		"""
		Get size of metadata.toml
		"""
		return self._fetch_meta_stat()["size"]

	@property
	def meta_mtime(self) -> float:
		"""
		Get last modified timestamp for metadata.toml
		"""
		return self._fetch_meta_stat()["mtime"]	

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

@dataclass
class projdb(Mapping):
	"""
	Database of scientific research projects
	:ivar projects: List of projects
	:ivar root: The path to the database root directory
	:ivar manifest: The path to a manifest json file
	:ivar autosave: Write detected changes back to the manifest?
	:ivar _index: Mapping of projects by name (case-insensitive)
	"""
	projects: list[projdata] = field(default_factory=list)
	root: str | None = None
	manifest: str | None = None
	autosave: bool | None = None
	_index: dict[str, projdata] | None = None

	def __post_init__(self):
		if self.root is not None:
			self.root = mkpath(self.root, must_exist=True)
		if self.manifest is not None:
			self.manifest = mkpath(self.manifest)
		if self.autosave is None:
			if self.root is None:
				self.autosave = False
			else:
				self.autosave = True
		if self.autosave and self.manifest is None:
			self.manifest = os.path.join(self.root, "manifest.json")
		self.ensure()

	def __getitem__(self, key: str) -> projdata | None:
		"""
		Get a projdata item from the database index
		"""
		return self._fetch_index()[key.casefold()]

	def __len__(self) -> int:
		"""
		Get the number of projects in the database index
		"""
		return len(self._fetch_index())

	def __iter__(self):
		"""
		Get an iterator over the database index keys
		"""
		return iter(self._fetch_index())

	def _fetch_index(self) -> dict[str, projdata]:
		"""
		Rebuild the index by project name
		"""
		if self._index is None:
			self._index = {
				proj.name.casefold(): proj 
				for proj in self.projects}
		return self._index

	def _reload_from_root(self) -> None:
		"""
		Reloads projects by scanning from the database root
		"""
		if not os.path.isdir(self.root):
			raise NotADirectoryError(f"root must be a directory: {self.root}")
		paths = tree_find(self.root, r"^metadata\.toml$", prune_on_match=True)
		self.projects = [projdata.from_path(p) for p in paths]
		self._index = None

	def _reload_from_manifest(self) -> None:
		"""
		Reloads projects by reading the database manifest
		"""
		with open(self.manifest) as f:
			self.projects = [projdata.from_dict(d) for d in json.load(f)]
			self._index = None

	def _reload_and_fetch_changes(self) -> list[projdata]:
		"""
		Fetch cached metadata from manifest and return changed projects
		"""
		self._reload_from_root()
		with open(self.manifest) as f:
			manifest = [projdata.from_dict(d) for d in json.load(f)]
		cache = {proj.path: proj for proj in manifest}
		changelist = []
		for proj in self.projects:
			cached = cache.get(proj.path)
			if cached is None or proj.meta_hash != cached.meta_hash:
				changelist.append(proj)
			else:
				proj.meta = cached.meta
		return changelist

	def root_exists(self) -> bool:
		"""
		Checks if the database root exists
		"""
		return self.root is not None and os.path.isdir(self.root)

	def manifest_exists(self) -> bool:
		"""
		Checks if the database manifest exists
		"""
		return self.manifest is not None and os.path.exists(self.manifest)

	def find(self, path: str) -> projdata:
		"""
		Find a project by its path
		:param path: The (real) path to the project directory
		:raises ValueError: If no matching project is found
		"""
		path = mkpath(path)
		for proj in self.values():
			if proj.is_local():
				if os.path.samefile(proj.path, path):
					return proj
			else:
				if mkpath(proj.path) == path:
					return proj
		raise ValueError(f"no project found for {path}")

	def filter(self, function: Callable[[projdata], bool]) -> projdb:
		"""
		Filter the projects and return a new projdb
		:param function: A function returning True for projdata to keep
		:returns: A new projdb (referencing original projects)
		"""
		return projdb([proj for proj in self.projects if function(proj)])

	def subset(self,
		names: Collection[str] | None = None,
		scope: Collection[str] | None = None,
		group: Collection[str] | None = None) -> projdb:
		"""
		Subset the projects and return a new projdb
		:param names: Patterns of names to keep
		:param scope: Patterns of scopes to keep
		:param group: Patterns of groups to keep
		:returns: A new projdb (referencing original projects)
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
		reverse: bool = False) -> projdb:
		"""
		Sort projects based on a key function and return a new projdb
		:param key: A function taking a projdata returning a comparable key
		:param reverse: Sort in descending order?
		:returns: A new projdb (referencing original projects)
		"""
		return projdb(sorted(self.projects, key=key, reverse=reverse))

	def sorted_by(self,
		*stats: str,
		reverse: bool = False) -> projdb:
		"""
		Return projects in ascending sort order by project tree stats
		:param stats: One or more of ('name', 'size', 'mtime')
		:param reverse: Sort in descending order?
		:returns: A new projdb (referencing original projects)
		"""
		expected = ("name", "size", "mtime")
		if stats is None or not all(st in expected for st in stats):
			raise ValueError(f"expected one or more of: {expected}")
		return self.sorted(key=attrgetter(*stats), reverse=reverse)

	def search(self, 
		pattern: str, 
		within: Collection[str] | None = None,
		ignore_case: bool = False,
		context_width: int = 60) -> list[projsearch]:
		"""
		Search indexed metadata for a regular expression
		:param pattern: The search pattern
		:param within: List of metadata fields to search; None means all
		:param ignore_case: Should case be ignored?
		:param context_width: Width of a context window for hits
		:returns: A list of projsearch objects with nonzero hits
		"""
		hits = []
		for proj in self.projects:
			hit = proj.meta.search(pattern, within, ignore_case, context_width)
			if hit is not None:
				hits.append(hit)
		return hits

	def ensure(self) -> None:
		"""
		Ensures the database is in a valid state
		"""
		if self.root_exists() and self.manifest_exists():
			changelist = self._reload_and_fetch_changes()
			if self.autosave and len(changelist) > 0:
				self.save()
		elif self.root_exists():
			self._reload_from_root()
			if self.autosave and self.manifest is not None:
				self.save()
		elif self.manifest_exists():
			self._reload_from_manifest()
		self._index = None

	def save(self, indent: int = "\t") -> None:
		"""
		Saves the database to the manifest
		:param indent: Number of spaces to indent json
		"""
		if self.manifest is None:
			raise ValueError("manifest must be a valid filepath")
		outlist = [proj.to_dict() for proj in self.projects]
		with open(self.manifest, "w") as f:
			json.dump(outlist, f, indent=indent)
