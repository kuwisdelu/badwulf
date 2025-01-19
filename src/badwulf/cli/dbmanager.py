
import os
import sys
import subprocess
import argparse
import datetime

from ..expdb import expdb
from ..tools import badwulf_attribution
from ..tools import print_datasets
from ..tools import format_bytes

class dbmanager:
	"""
	Command line utility for scientific dataset management
	"""
	
	def __init__(self,
		name,
		dbpath,
		dbname,
		version,
		date,
		description,
		readme = None,
		program = None,
		metaname = True,
		username = None,
		remote_dbhost = None,
		remote_dbpath = None,
		server = None,
		server_username = False,
		port = None):
		"""
		Initialize a cluster CLI utility program
		:param name: The name of the cluster/server
		:param dbpath: The local database path
		:param dbname: The database name
		:param version: The version of the program
		:param date: The date of the program's last revision
		:param description: A description of the program
		:param readme: The file path of a README.md file
		:param program: The name of the program (defaults to name)
		:param metaname: Subdirectory containing "manifest.toml"" (optional)
		:param username: Your username on the cluster
		:param remote_dbhost: The remote database host
		:param remote_dbpath: The remote database path
		:param server: The gateway server hostname (optional)
		:param server_username: Your username on the gateway server (optional)
		:param port: The local port for gateway server SSH forwarding
		"""
		self.name = name
		self.dbpath = dbpath
		self.dbname = dbname
		self.version = version
		if isinstance(date, datetime.date):
			self.date = date
		else:
			self.date = datetime.date.fromisoformat(date)
		self.description = description
		self.readme = readme
		if program is None:
			self.program = name.casefold()
		else:
			self.program = program
		self.metaname = metaname
		self.username = username
		self.remote_dbhost = remote_dbhost
		self.remote_dbpath = remote_dbpath
		self.server = server
		self.server_username = server_username
		self.port = port
		self._parser = None
		self._args = None

	def _add_server_args(self, parser):
		"""
		Add server parameters to a parser.
		:param parser: The parser to update
		"""
		parser.add_argument("-p", "--port", action="store",
			help="port forwarding", default=self.port)
		parser.add_argument("-u", "--user", action="store",
			help=f"{self.name} user", default=self.username)
		parser.add_argument("-L", "--login", action="store",
			help="gateway server user", default=self.server_username)
		parser.add_argument("-S", "--server", action="store",
			help="gateway server host", default=self.server)
		parser.add_argument("--remote-host", action="store",
			help="remote database host", default=self.remote_dbhost)
		parser.add_argument("--remote-path", action="store",
			help="remote database path", default=self.remote_dbpath)
	
	def _add_subcommand_ls(self, subparsers):
		"""
		Add 'ls' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("ls", 
			help="list all datasets")
		cmd.add_argument("-l", "--long", action="store_true",
			help="show extended details")
		cmd.add_argument("-s", "--scope", action="store",
			help="filter by scope")
		cmd.add_argument("-g", "--group", action="store",
			help="filter by group")
	
	def _add_subcommand_ls_cache(self, subparsers):
		"""
		Add 'ls-cache' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("ls-cache", 
			help="list cached datasets")
		cmd.add_argument("-l", "--long", action="store_true",
			help="show extended details")
		cmd.add_argument("-s", "--scope", action="store",
			help="filter by scope")
		cmd.add_argument("-g", "--group", action="store",
			help="filter by group")
		cmd.add_argument("--sort", action="store",
			help="sort by file attribute (atime, mtime, size)")
		cmd.add_argument("--reverse", action="store",
			help="reverse by file attribute (atime, mtime, size)")
	
	def _add_subcommand_search(self, subparsers):
		"""
		Add 'search' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("search", 
			help="search all datasets")
		cmd.add_argument("pattern", action="store",
			help="search pattern (regex allowed)")
		cmd.add_argument("-s", "--scope", action="store",
			help="filter by scope")
		cmd.add_argument("-g", "--group", action="store",
			help="filter by group")
	
	def _add_subcommand_search_cache(self, subparsers):
		"""
		Add 'search-cache' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("search-cache", 
			help="search cached datasets")
		cmd.add_argument("pattern", action="store",
			help="search pattern (regex allowed)")
		cmd.add_argument("-s", "--scope", action="store",
			help="filter by scope")
		cmd.add_argument("-g", "--group", action="store",
			help="filter by group")
		
	def _add_subcommand_prune_cache(self, subparsers):
		"""
		Add 'prune-cache' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("prune-cache", 
			help="remove cached datasets")
		cmd.add_argument("limit", action="store",
			help="maximum cache size (10, 100, 1000, etc.)", type=float)
		cmd.add_argument("units", action="store",
			help="cache size units (MB, GB, TB, etc.)")
		cmd.add_argument("-s", "--scope", action="store",
			help="filter by scope")
		cmd.add_argument("-g", "--group", action="store",
			help="filter by group")
		cmd.add_argument("-L", "--lru", action="store_const",
			help="prune least recently used (default)", dest="strategy", const="lru")
		cmd.add_argument("-M", "--mru", action="store_const",
			help="prune most recently used", dest="strategy", const="mru")
		cmd.add_argument("-B", "--big", action="store_const",
			help="prune largest files", dest="strategy", const="big")
		cmd.add_argument("-S", "--small", action="store_const",
			help="prune smallest files", dest="strategy", const="small")
		cmd.add_argument("--ask", action="store_true",
			help="ask to confirm before deleting?")
		cmd.add_argument("--dry-run", action="store_true",
			help="show what would happen without doing it?")
	
	def _add_subcommand_describe(self, subparsers):
		"""
		Add 'describe' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("describe", 
			help="describe a dataset")
		cmd.add_argument("id", action="store",
			help="the identifier of the dataset to describe")
	
	def _add_subcommand_sync(self, subparsers):
		"""
		Add 'sync' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("sync", 
			help="sync a dataset to local cache")
		cmd.add_argument("id", action="store",
			help="the identifier of the dataset to sync")
		self._add_server_args(cmd)
		cmd.add_argument("-f", "--force", action="store_true",
			help="force re-sync if already cached")
		cmd.add_argument("--ask", action="store_true",
			help="ask to confirm before syncing?")
		cmd.add_argument("--dry-run", action="store_true",
			help="show what would happen without doing it?")
	
	def _add_subcommand_submit(self, subparsers):
		"""
		Add 'submit' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("submit", 
			help="submit a dataset")
		cmd.add_argument("path", action="store",
			help="the path to the dataset directory")
		self._add_server_args(cmd)
		cmd.add_argument("-f", "--force", action="store_true",
			help="force re-submission if already tracked")
		cmd.add_argument("--ask", action="store_true",
			help="ask to confirm before submitting?")
		cmd.add_argument("--dry-run", action="store_true",
			help="show what would happen without doing it?")
	
	def _add_subcommand_status(self, subparsers):
		"""
		Add 'status' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("status", 
			help="report status of cache against manifest")
		cmd.add_argument("-l", "--long", action="store_true",
			help="show extended details")
		cmd.add_argument("-s", "--scope", action="store",
			help="filter by scope")
		cmd.add_argument("-g", "--group", action="store",
			help="filter by group")
	
	def _add_subcommand_readme(self, subparsers):
		"""
		Add 'readme' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("readme", 
			help="display readme")
		cmd.add_argument("-p", "--pager", action="store",
			help="program to display readme (default 'glow')")
		cmd.add_argument("-w", "--width", action="store",
			help="word-wrap readme at width (default 70)", default=70)

	def _init_parser(self):
		"""
		Initialize the argument parser
		"""
		parser = argparse.ArgumentParser(self.program,
			description=self.description)
		parser.add_argument("-v", "--version", action="store_true",
			help="display version")
		subparsers = parser.add_subparsers(dest="cmd")
		self._add_subcommand_ls(subparsers)
		self._add_subcommand_ls_cache(subparsers)
		self._add_subcommand_search(subparsers)
		self._add_subcommand_search_cache(subparsers)
		self._add_subcommand_prune_cache(subparsers)
		self._add_subcommand_describe(subparsers)
		self._add_subcommand_sync(subparsers)
		self._add_subcommand_submit(subparsers)
		self._add_subcommand_status(subparsers)
		if self.readme is not None:
			self._add_subcommand_readme(subparsers)
		self._parser = parser
	
	def parse_args(self):
		"""
		Parse command line arguments
		"""
		if self._parser is None:
			self._init_parser()
		self._args = self._parser.parse_args()
	
	def open_db(self):
		"""
		Open connection to the database
		:param dbpath: The local database path
		"""
		# check for valid database path
		if not os.path.isdir(self.dbpath):
			raise NotADirectoryError(f"database does not exist: '{self.dbpath}'")
		# connect and return database
		db = expdb(self.username, self.dbpath, self.dbname,
			metaname=self.metaname,
			remote_dbhost=self.remote_dbhost,
			remote_dbpath=self.remote_dbpath,
			server=self.server,
			server_username=self.server_username,
			port=self.port,
			verbose=False,
			autoconnect=False)
		return db
	
	def main(self):
		"""
		Run the program
		"""
		if self._args is None:
			self.parse_args()
		args = self._args
		# version
		if args.version:
			description = self.description.splitlines()[0]
			print(f"{description} version {self.version} (revised {self.date})")
			print(badwulf_attribution())
			sys.exit()
		# help
		if args.cmd is None:
			self._parser.print_help()
		else:
			db = self.open_db()
		# ls
		if args.cmd == "ls":
			datasets = db.ls(
				scope=args.scope,
				group=args.group,
				details=args.long)
			if args.long:
				print_datasets(datasets)
			else:
				for name in datasets:
					print(f"['{name}']")
		# ls-cache
		elif args.cmd == "ls-cache":
			sort = args.sort is not None or args.reverse is not None
			datasets = db.ls_cache(
				scope=args.scope,
				group=args.group,
				details=args.long or sort)
			if sort:
				if args.reverse is not None:
					args.sort = args.reverse
					args.reverse = True
				sortby = args.sort.casefold()
				if sortby == "size".casefold():
					datasets.sort(key=lambda x: x.size)
				elif sortby == "atime".casefold():
					datasets.sort(key=lambda x: x.atime)
				elif sortby == "mtime".casefold():
					datasets.sort(key=lambda x: x.mtime)
				else:
					sys.exit(f"msi ls-cache: error: can't sort by attribute: '{args.sort}'")
				if args.reverse:
					datasets.reverse()
			if sort or args.long:
				print_datasets(datasets)
				sizes = [x.size for x in datasets]
				print(f"~= {format_bytes(sum(sizes))} total")
			else:
				for name in datasets:
					print(f"['{name}']")
		# search
		elif args.cmd == "search":
			hits = db.search(
				pattern=args.pattern,
				scope=args.scope,
				group=args.group)
			print_datasets(hits)
		# search-cache
		elif args.cmd == "search-cache":
			hits = db.search_cache(
				pattern=args.pattern,
				scope=args.scope,
				group=args.group)
			print_datasets(hits)
		# prune-cache
		elif args.cmd == "prune-cache":
			if args.strategy is None:
				args.strategy = "lru"
			db.prune_cache(
				limit=args.limit,
				units=args.units,
				scope=args.scope,
				group=args.group,
				strategy=args.strategy,
				dry_run=args.dry_run, ask=args.ask)
		# describe
		elif args.cmd == "describe":
			dataset = db.get(args.id)
			if dataset is None:
				sys.exit(f"msi describe: error: no such dataset: '{args.id}'")
			else:
				print(dataset.describe())
				if args.id in db.cache:
					print(db.cache.get(args.id).describe(dataset.formats))
		# sync
		elif args.cmd == "sync":
			if args.id in db.cache and not args.force:
				sys.exit("msi sync: dataset is already cached; use --force to re-sync")
			db.username = args.username
			db.remote_dbhost = args.remote_host
			db.remote_dbpath = args.remote_path
			db.server = args.server
			db.server_username = args.login
			db.port = args.port
			db.sync(args.id,
				force=args.force,
				dry_run=args.dry_run, ask=args.ask)
		# submit
		elif args.cmd == "submit":
			name = os.path.basename(args.path)
			if name in db.manifest and not args.force:
				sys.exit("msi submit: dataset is already tracked; use --force to re-submit")
			db.username = args.username
			db.remote_dbhost = args.remote_host
			db.remote_dbpath = args.remote_path
			db.server = args.server
			db.server_username = args.login
			db.port = args.port
			db.submit(args.path,
				force=args.force,
				dry_run=args.dry_run, ask=args.ask)
		# status
		elif args.cmd == "status":
			synced, remoteonly, localonly = db.status(
				scope=args.scope,
				group=args.group,
				details=args.long)
			msg_synced = "\n~~~~ synced:"
			msg_remoteonly = "\n>>>> tracked but not cached:"
			msg_localonly = "\n<<<< cached but not tracked:"
			if args.long:
				print(msg_synced)
				print_datasets(synced)
				print(msg_remoteonly)
				print_datasets(remoteonly)
				print(msg_localonly)
				print_datasets(localonly)
			else:
				print(msg_synced)
				for name in synced:
					print(f"['{name}']")
				print(msg_remoteonly)
				for name in remoteonly:
					print(f"['{name}']")
				print(msg_localonly)
				for name in localonly:
					print(f"['{name}']")
		# readme
		elif args.cmd == "readme":
			if args.pager is None:
				cmd = ["glow", "-p", "-w", str(args.width)]
			else:
				cmd = [args.pager]
			cmd += [self.readme]
			subprocess.run(cmd)
		sys.exit()
