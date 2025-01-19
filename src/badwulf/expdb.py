
# Experiment data manager

import os
import sys
if sys.version_info >= (3, 11):
	import tomllib
else:
	import tomli as tomllib

import shutil
from time import sleep
from dataclasses import dataclass
from dataclasses import asdict
from datetime import datetime

from .rssh import rssh
from .tools import ls
from .tools import fix_path
from .tools import dirsize
from .tools import dirfiles
from .tools import to_bytes
from .tools import format_bytes
from .tools import format_datasets
from .tools import print_datasets
from .tools import askYesNo
from .tools import grep1
from .tools import grepl

# scopes
SCOPE_PRIVATE = "Private"
SCOPE_PROTECTED = "Protected"
SCOPE_PUBLIC = "Public"
SCOPE_XFER = "Xfer"

@dataclass
class expdata:
	"""
	Experimental metadata for a scientific dataset
	"""

	name: str
	scope: str
	group: str
	title: str
	description: str
	sample_processing: str
	data_processing: str
	contact: dict
	url: dict
	date: dict
	formats: list
	keywords: list
	notes: list
	
	def __init__(self, name, entry, printwidth = 60):
		"""
		Initialize an expdata instance
		:param name: The name of the dataset
		:param entry: A dict parsed from its manifest entry
		"""
		self.name = name
		self.scope = entry["scope"]
		self.group = entry["group"]
		self.title = entry["title"]
		self.description = entry["description"]
		self.sample_processing = entry.get("sample-processing", "")
		self.data_processing = entry.get("data-processing", "")
		self.contact = entry.get("contact", [])
		self.url = entry.get("url", {})
		self.date = entry.get("date", {})
		self.formats = entry.get("formats", [])
		self.keywords = entry.get("keywords", [])
		self.notes = entry.get("notes", [])
		self.printwidth = printwidth
	
	def __str__(self):
		"""
		Return str(self)
		"""
		return self.describe(self.printwidth)
	
	def describe(self, printwidth = None):
		"""
		Return dataset description
		"""
		dataset = asdict(self)
		printed = ["scope", "group", "description",
			"sample_processing", "data_processing",
			"formats", "keywords"]
		notprinted = set(dataset.keys()).difference(printed)
		notprinted = notprinted.difference(["name", "title"])
		if len(dataset["notes"]) > 0:
			notprinted = notprinted.difference(["notes"])
		title = self.title
		if ( len(title) > 0 ):
			sl = [f" {title}: "]
		else:
			sl = [" <Untitled>: "]
		sl.append(" {")
		for field in printed:
			value = dataset[field]
			if isinstance(value, str):
				if printwidth is not None:
					if len(value) > printwidth:
						value = value[:printwidth - 4] + "..."
			else:
				value = ", ".join(value)
			sl.append(f"  {field}: {value}")
		for i, note in enumerate(dataset["notes"]):
			if printwidth is not None:
				if len(note) > printwidth:
					note = note[:printwidth - 4] + "..."
			sl.append(f"  note {i + 1}: {note}")
		more_fields = [f"'{field}'" for field in sorted(notprinted)]
		more_fields = ", ".join(more_fields)
		sl.append(f"  additional fields: {more_fields}")
		sl.append(" }")
		return "\n".join(["{"] + sl + ["}"])
	
	def search(self, pattern, context_width = 60):
		"""
		Search all metadata fields for a pattern
		:param pattern: The search pattern
		:param context_width: Width of a context window to return
		:returns: An expsearch instance or None
		"""
		search = expsearch(self, pattern, context_width=context_width)
		if len(search.hits) > 0:
			return search
		else:
			return None
	
	def has_scope(self, pattern):
		"""
		Detect if the dataset's scope matches a pattern
		:param pattern: The scope pattern
		:returns: bool
		"""
		return grep1(pattern, self.scope) is not None
	
	def has_group(self, pattern):
		"""
		Detect if the dataset's group matches a pattern
		:param pattern: The group pattern
		:returns: bool
		"""
		return grep1(pattern, self.group) is not None

@dataclass
class expsearch:
	"""
	Experimental metadata search hits
	"""

	name: str
	title: str
	scope: str
	group: str
	pattern: str
	hits: list
	
	def __init__(self, dataset, pattern, context_width = 60):
		"""
		Initialize an expsearch instance
		:param dataset: An expdata instance
		:param pattern: The search pattern
		:param context_width: Width of a context window to return
		"""
		self.name = dataset.name
		self.title = dataset.title
		self.scope = dataset.scope
		self.group = dataset.group
		self.pattern = pattern
		hits = {}
		title = grep1(pattern, dataset.title,
			context_width=context_width)
		description = grep1(pattern, dataset.description,
			context_width=context_width)
		sample_processing = grep1(pattern, dataset.sample_processing,
			context_width=context_width)
		data_processing = grep1(pattern, dataset.data_processing,
			context_width=context_width)
		if title is not None:
			hits["title"] = title
		if description is not None:
			hits["description"] = description
		if sample_processing is not None:
			hits["sample_processing"] = sample_processing
		if data_processing is not None:
			hits["data_processing"] = data_processing
		for i, contact in enumerate(dataset.contact):
			if any(grepl(pattern, contact.values())):
				hits[f"contact {i + 1}"] = contact
		for i, format_ in enumerate(dataset.formats):
			if grep1(pattern, format_) is not None:
				hits[f"format {i + 1}"] = format_
		for i, keyword in enumerate(dataset.keywords):
			if grep1(pattern, keyword) is not None:
				hits[f"keyword {i + 1}"] = keyword
		for i, note in enumerate(dataset.notes):
			if grep1(pattern, note) is not None:
				hits[f"note {i + 1}"] = note
		self.hits = hits
		self.printwidth = dataset.printwidth
	
	def __str__(self):
		"""
		Return str(self)
		"""
		title = self.title
		if ( len(title) > 0 ):
			sl = [f" {title}: "]
		else:
			sl = [" <Untitled>: "]
		sl.append(" {")
		sl.append("  _search pattern_: " + self.pattern)
		sl.append("  _no. of matches_: " + str(len(self.hits)))
		sl.append("  scope: " + str(self.scope))
		sl.append("  group: " + str(self.group))
		for field, match in self.hits.items():
			if len(match) > self.printwidth:
				match = match[:self.printwidth - 4] + "..."
			sl.append(f"  >{field}: {match}")
		sl.append(" }")
		return "\n".join(["{"] + sl + ["}"])

@dataclass
class expcache:
	"""
	File metadata for a cached dataset
	"""

	name: str
	path: str
	_atime: float
	_mtime: float
	size: int
	
	def __init__(self, name, path, atime, mtime, size):
		"""
		Initialize an expcache instance
		:param name: The name of the dataset
		:param path: The file path to the dataset
		:param atime: Last access time
		:param mtime: Last modified time
		:param size: Total size in storage
		"""
		self.name = name
		self.path = path
		self._atime = atime
		self._mtime = mtime
		self.size = size
	
	@property
	def atime(self):
		"""
		Get last accessed time
		"""
		return datetime.fromtimestamp(self._atime)
	
	@property
	def mtime(self):
		"""
		Get last modified time
		"""
		return datetime.fromtimestamp(self._mtime)
	
	def __str__(self):
		"""
		Return str(self)
		"""
		return self.describe()
	
	def describe(self, printformats = None):
		"""
		Return cached dataset description
		"""
		path = f" path: '{self.path}'"
		atime = f" atime: '{self.atime}'"
		mtime = f" mtime: '{self.mtime}'"
		size = f" size: {format_bytes(self.size)}"
		sl = [path, atime, mtime, size]
		if printformats is not None:
			files = []
			fmts = [f"{fmt}$" for fmt in printformats]
			for pattern in fmts:
				files.extend(dirfiles(self.path, pattern, recursive=True))
			files = [f" file {str(i + 1)}: '{file}'" 
				for i, file 
				in enumerate(files)]
			sl.extend(files)
			sl = [" " + s for s in sl]
			sl = [" Cached:", " {"] + sl + [" }"]
		return "\n".join(["{"] + sl + ["}"])

class expdb:
	"""
	Database manager for experimental datasets and metadata
	"""
	
	def __init__(self, username, dbpath, dbname, metaname = True,
		remote_dbhost = None, remote_dbpath = None,
		server = None, server_username = None,
		port = 8080, remote_port = 22, verbose = False,
		autoconnect = True):
		"""
		Initialize an expdb instance
		:param username: Your username on remote database host
		:param dbpath: The local database path
		:param dbname: The database name (may be None)
		:param metaname: Subdirectory containing "manifest.toml"" (optional)
		:param remote_dbhost: The remote database host
		:param remote_dbpath: The remote database path
		:param server: The gateway server hostname (optional)
		:param server_username: Your username on the gateway server (optional)
		:param port: The local port for gateway server SSH forwarding
		:param remote_port: The remote database host port
		:param verbose: Print progress messages?
		:param autoconnect: Connect on initialization?
		"""
		if remote_dbhost is not None and remote_dbpath is None:
			remote_dbpath = dbpath
		self.username = username
		self.dbpath = fix_path(dbpath, must_exist=True)
		self.dbname = dbname
		if metaname in (True, False):
			if metaname:
				metaname = dbname
			else:
				metaname = None
		self.metaname = metaname
		self.remote_dbhost = remote_dbhost
		self.remote_dbpath = remote_dbpath
		self.server = server
		self.server_username = server_username
		self.port = port
		self.remote_port = remote_port
		self.verbose = verbose
		self._manifest = None
		self._cache = None
		if autoconnect:
			self.open()
	
	def __str__(self):
		"""
		Return str(self)
		"""
		return format_datasets(self.manifest.values())
	
	def __repr__(self):
		"""
		Return repr(self)
		"""
		user = f"username='{self.username}'"
		dbpath = f"dbpath='{self.dbpath}'"
		fields = [user, dbpath]
		if self.remote_dbhost is not None:
			remote_dbhost = f"remote_dbhost='{self.remote_dbhost}'"
			fields.append(remote_dbhost)
			if self.remote_dbpath is not None:
				remote_dbpath = f"remote_dbpath='{self.remote_dbpath}'"
				fields.append(remote_dbpath)
		if self.server is not None:
			server = f"server='{self.server}'"
			if self.server_username is None:
				server_username = "server_username=None"
			else:
				server_username = f"server_username='{self.server_username}'"
			port = f"port={self.port}"
			fields.extend([server, server_username, port])
		fields = ", ".join(fields)
		return f"expdb({fields})"
		
	def __enter__(self):
		"""
		Enter context manager
		"""
		self.open_manifest()
		return self
	
	def __exit__(self, exc_type, exc_value, traceback):
		"""
		Exit context manager
		"""
		self.close()
	
	def __del__(self):
		"""
		Delete self
		"""
		self.close()
	
	def __getitem__(self, key):
		"""
		Return db[key]
		"""
		return self.get(key)
	
	@property
	def manifest(self):
		"""
		Get dataset manifest
		"""
		if self._manifest is None:
			self.open_manifest()
		return self._manifest
	
	@property
	def cache(self):
		"""
		Get local cache
		"""
		if self._cache is None:
			self.open_cache()
		return self._cache
	
	@property
	def dbdir(self):
		"""
		Resolve local cache directory
		"""
		if self.dbpath is None:
			return None
		if self.dbname is None:
			return self.dbpath
		else:
			return os.path.join(self.dbpath, self.dbname)
	
	@property
	def remote_dbdir(self):
		"""
		Resolve remote database directory
		"""
		if self.remote_dbpath is None:
			return None
		if self.dbname is None:
			return self.remote_dbpath
		else:
			return os.path.join(self.remote_dbpath, self.dbname)
	
	def get(self, key):
		"""
		Return db[key]
		:param key: A dataset name or iterable of them
		:returns: An expdata instance or dict of them
		"""
		if isinstance(key, str):
			return self.manifest.get(key)
		else:
			return {ki: self.manifest[ki] for ki in key}
	
	def isopen(self):
		"""
		Check if the database is ready
		"""
		return self._manifest is not None or self._cache is not None
	
	def open(self):
		"""
		Ready the connection to the database
		"""
		self.open_manifest()
		self.open_cache()
	
	def open_manifest(self):
		"""
		Refresh the database manifest
		"""
		if self.metaname is None:
			path = os.path.join(self.dbdir, "manifest.toml")
		else:
			path = os.path.join(self.dbdir, self.metaname, "manifest.toml")
		path = fix_path(path, must_exist=True)
		if self.verbose:
			print(f"parsing '{path}'")
		with open(path, "rb") as file:
			manifest = tomllib.load(file)
			manifest = {name: expdata(name, entry) 
				for name, entry in manifest.items()}
			self._manifest = manifest
		if self.verbose:
			print("manifest is searchable")
	
	def open_cache(self):
		"""
		Refresh the cache metadata
		"""
		if self.verbose:
			print("detecting cached datasets")
		cache = []
		cache.extend(self._get_cached_scope(SCOPE_PRIVATE))
		cache.extend(self._get_cached_scope(SCOPE_PROTECTED))
		cache.extend(self._get_cached_scope(SCOPE_PUBLIC))
		self._cache = {dataset.name: dataset for dataset in cache}
		if self.verbose:
			print(f"{len(cache)} datasets available locally")
	
	def _get_cached_dataset(self, scope, group, dataset):
		"""
		Get cached dataset metadata
		:param scope: The dataset scope
		:param group: The dataset group
		:param dataset: The dataset name
		:returns: An expcache instance
		"""
		path = os.path.join(self.dbdir, scope, group, dataset)
		path = fix_path(path, must_exist=True)
		size = dirsize(path, all_names=True)
		atime = os.path.getatime(path)
		mtime = os.path.getmtime(path)
		return expcache(name=dataset, path=path,
			atime=atime, mtime=mtime, size=size)
	
	def _get_cached_group(self, scope, group):
		"""
		Get list of cached group metadata
		:param scope: The dataset scope
		:param group: The dataset group
		:returns: A list of expcache instances
		"""
		path = os.path.join(self.dbdir, scope, group)
		path = fix_path(path, must_exist=True)
		return [self._get_cached_dataset(scope, group, dataset)
			for dataset
			in ls(path)]
	
	def _get_cached_scope(self, scope):
		"""
		Get list of cached scope metadata
		:param scope: The dataset scope
		:returns: A list of expcache instances
		"""
		path = os.path.join(self.dbdir, scope)
		groups = []
		if os.path.isdir(path):
			path = fix_path(path, must_exist=True)
			for group in ls(path):
				groups.extend(self._get_cached_group(scope, group))
		return groups
	
	def ls(self, scope = None, group = None, details = False):
		"""
		List all datasets by name
		:param scope: Filter by scope
		:param group: Filter by group
		:param details: Return names only or dataset details?
		:returns: A list of datasets
		"""
		if scope is None and group is None:
			if details:
				return list(self.manifest.values())
			else:
				return list(self.manifest.keys())
		else:
			results = []
			for name, dataset in self.manifest.items():
				ok = True
				if scope is not None:
					ok = ok and dataset.has_scope(scope)
				if group is not None:
					ok = ok and dataset.has_group(group)
				if ok:
					if details:
						results.append(dataset)
					else:
						results.append(name)
			return results
	
	def ls_cache(self, scope = None, group = None, details = False):
		"""
		List cached datasets by name
		:param scope: Filter by scope
		:param group: Filter by group
		:param details: Return names only or dataset details?
		:returns: A list of datasets
		"""
		if scope is None and group is None:
			if details:
				return list(self.cache.values())
			else:
				return list(self.cache.keys())
		else:
			results = []
			for name in self.cache.keys():
				ok = True
				dataset = self.get(name)
				if dataset is None:
					continue
				if scope is not None:
					ok = ok and dataset.has_scope(scope)
				if group is not None:
					ok = ok and dataset.has_group(group)
				if ok:
					if details:
						results.append(self.cache.get(name))
					else:
						results.append(name)
			return results
	
	def search(self, pattern = None, scope = None, group = None):
		"""
		Search all dataset metadata for a pattern
		:param pattern: The pattern to find
		:param scope: Filter by scope
		:param group: Filter by group
		:returns: A list of search hits
		"""
		hits = []
		for name, dataset in self.manifest.items():
			ok = True
			if scope is not None:
				ok = ok and dataset.has_scope(scope)
			if group is not None:
				ok = ok and dataset.has_group(group)
			if ok and pattern is not None:
				result = dataset.search(pattern)
				if result is not None:
					hits.append(result)
		return hits
	
	def search_cache(self, pattern = None, scope = None, group = None):
		"""
		Search cached dataset metadata for a pattern
		:param pattern: The pattern to find
		:param scope: Filter by scope
		:param group: Filter by group
		:returns: A list of search hits
		"""
		hits = []
		for name in self.cache.keys():
			ok = True
			dataset = self.get(name)
			if dataset is None:
				continue
			if scope is not None:
				ok = ok and dataset.has_scope(scope)
			if group is not None:
				ok = ok and dataset.has_group(group)
			if ok and pattern is not None:
				result = dataset.search(pattern)
				if result is not None:
					hits.append(result)
		return hits
	
	def prune_cache(self, limit, units, scope = None, group = None,
		strategy = "lru", dry_run = False, ask = False):
		"""
		List cached datasets by name
		:param limit: Maximum size of the cache
		:param units: Size units (B, KB, MB, GB, TB, etc.)
		:param strategy: One of "lru", "mru", "big", "small"
		:param dry_run: Show what would be done without doing it?
		:param ask: Confirm before deleting?
		"""
		limit = to_bytes(limit, units)
		cache = self.ls_cache(scope, group, details=True)
		strategy = strategy.casefold()
		if strategy == "lru".casefold():
			cache.sort(key=lambda x: x.atime)
		elif strategy == "mru".casefold():
			cache.sort(key=lambda x: x.atime)
			cache.reverse()
		elif strategy == "big".casefold():
			cache.sort(key=lambda x: x.size)
			cache.reverse()
		elif strategy == "small".casefold():
			cache.sort(key=lambda x: x.size)
		else:
			raise ValueError(f"invalid strategy: {strategy}")
		sizes = [x.size for x in cache]
		totsize = sum(sizes)
		delsize = []
		for i in range(len(sizes)):
			delsize.append(totsize - sum(sizes[:i]))
		target = 0
		while delsize[target] > limit:
			target += 1
		newsize = totsize - sum(sizes[:target])
		print(f"the local cache is currently {format_bytes(totsize)}")
		print(f"using strategy: {strategy}")
		print("the following datasets will be deleted from the cache:")
		print_datasets(cache[:target], names_only=True)
		print(f"~= {format_bytes(sum(sizes[:target]))} will be freed")
		if not target:
			return
		if ask and not askYesNo():
			return
		if not dry_run:
			for x in cache[:target]:
				print(f"deleting '{x.path}'")
				try:
					shutil.rmtree(fix_path(x.path, must_exist=True))
				except Exception:
					print(f"failed to delete '{x.path}'")
			print(f"the local cache is now {format_bytes(newsize)}")
		return
	
	def sync(self, name, force = False, dry_run = False, ask = False):
		"""
		Sync a dataset to local storage
		:param name: The name of the dataset
		:param force: Should the dataset be re-synced if already cached?
		:param dry_run: Show what would be done without doing it?
		:param ask: Confirm before downloading?
		"""
		if name not in self.manifest:
			raise KeyError(f"no such dataset: '{name}'")
		if name in self.cache and not force:
			print("dataset is already cached; use force=True to re-sync")
			return
		if self.remote_dbhost is None:
			raise IOError("remote host is None")
		if self.remote_dbpath is None:
			raise IOError("remote path is None")
		dataset = self.get(name)
		scope = dataset.scope
		group = dataset.group
		path = os.path.join(self.dbdir, scope, group)
		path = fix_path(path, must_exist=False)
		if not os.path.isdir(path):
			os.makedirs(path)
		src = os.path.join(self.remote_dbdir, scope, group, name)
		src = src + "/"
		dest = os.path.join(self.dbdir, scope, group, name)
		dest = dest + "/"
		try:
			con = rssh(self.username,
				destination=self.remote_dbhost,
				server=self.server,
				server_username=self.server_username,
				port=self.port,
				destination_port=self.remote_port)
			sleep(1) # allow time to connect
			con.download(src, dest, dry_run=dry_run, ask=ask)
			if os.path.isdir(dest):
				print("sync complete; refreshing cache metadata")
				self.open_cache()
		except Exception:
			print("a problem occured during syncing")
		finally:
			con.close()
	
	def submit(self, path, force = False, dry_run = False, ask = False):
		"""
		Submit a dataset to the database maintainer(s)
		:param path: The path to the data directory
		:param force: Should the dataset be re-submitted if already tracked?
		:param dry_run: Show what would be done without doing it?
		:param ask: Confirm before uploading?
		"""
		path = fix_path(path, must_exist=False)
		name = os.path.basename(path)
		if name in self.manifest and not force:
			print("dataset is already tracked; use force=True to re-submit")
			return
		if self.remote_dbhost is None:
			raise IOError("remote host is None")
		if self.remote_dbpath is None:
			raise IOError("remote path is None")
		if not os.path.isdir(path):
			raise NotADirectoryError(f"path must be a directory: {path}")
		if path[-1] != "/":
			src = path + "/"
		else:
			src = path
		dest = os.path.join(self.remote_dbdir, SCOPE_XFER, name)
		dest = dest + "/"
		try:
			con = rssh(self.username,
				destination=self.remote_dbhost,
				server=self.server,
				server_username=self.server_username,
				port=self.port,
				destination_port=self.remote_port)
			sleep(1) # allow time to connect
			con.upload(src, dest, dry_run=dry_run, ask=ask)
			print("submission complete")
		except Exception:
			print("a problem occured during submission")
		finally:
			con.close()
	
	def status(self, scope = None, group = None, details = False):
		"""
		Get status of cache versus manifest
		:param scope: Filter by scope
		:param group: Filter by group
		:param details: Return names only or dataset details?
		:returns: A tuple like (synced, remoteonly, localonly)
		"""
		remote = set(self.manifest.keys())
		local = set(self.cache.keys())
		synced = {name: dataset 
			for name, dataset 
			in self.cache.items()
			if name in remote.intersection(local)}
		remoteonly = {name: dataset 
			for name, dataset 
			in self.manifest.items()
			if name in remote.difference(local)}
		localonly = {name: dataset 
			for name, dataset 
			in self.cache.items()
			if name in local.difference(remote)}
		if scope is None and group is None:
			if details:
				synced_list = list(synced.values())
				remoteonly_list = list(remoteonly.values())
				localonly_list = list(localonly.values())
			else:
				synced_list = list(synced.keys())
				remoteonly_list = list(remoteonly.keys())
				localonly_list = list(localonly.keys())
		else:
			synced_list = []
			remoteonly_list = []
			localonly_list = []
			for name in synced.keys():
				ok = True
				dataset = self.manifest.get(name)
				if dataset is None:
					continue
				if scope is not None:
					ok = ok and dataset.has_scope(scope)
				if group is not None:
					ok = ok and dataset.has_group(group)
				if ok:
					if details:
						synced_list.append(synced.get(name))
					else:
						synced_list.append(name)
			for name in remoteonly.keys():
				ok = True
				dataset = self.manifest.get(name)
				if dataset is None:
					continue
				if scope is not None:
					ok = ok and dataset.has_scope(scope)
				if group is not None:
					ok = ok and dataset.has_group(group)
				if ok:
					if details:
						remoteonly_list.append(remoteonly.get(name))
					else:
						remoteonly_list.append(name)
			if details:
				localonly_list = list(localonly.values())
			else:
				localonly_list = list(localonly.keys())
		return synced_list, remoteonly_list, localonly_list
	
	def close(self):
		"""
		Remove the connection to the database
		"""
		self._manifest = None
		self._cache = None
