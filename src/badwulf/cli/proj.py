
# Project management

import os
import json
import getpass
from datetime import date
from datetime import datetime
from dataclasses import asdict

from ..core import dbcontext
from ..util import prog_error
from ..util import format_bytes
from ..util import tokenize
from ..util import rtokenize

DEFAULT_SCOPE = "private"
DEFAULT_GROUP = "scratch"

def parse_sort(args):
	if len(args.sort) > 0:
		keys = args.sort
	elif len(args.reverse) > 0:
		keys = args.reverse
	else:
		keys = []
	keys.append("name")
	reverse = True if len(args.reverse) > 0 else False
	return keys, reverse

def add(args):
	ctx = dbcontext.from_default_locations()
	prefix, name = rtokenize(args.project)
	try:
		db = ctx.local_db(prefix)
		proj = db.create(
			name=name,
			scope=args.scope,
			group=args.group,
			title="",
			date={"created": date.today()},
			keywords=[],
			formats=[],
			contact=[{"name": getpass.getuser()}],
			description={"abstract": ""})
		print(f"Initialized {proj.meta_path}")
		db.save()
	except Exception as e:
		prog_error(e, args)

def edit(args):
	ctx = dbcontext.from_default_locations()
	prefix, name = rtokenize(args.project)
	try:
		proj = ctx.local_db(prefix)[name]
	except Exception as e:
		prog_error(e, args)
	editor = args.editor
	if editor is None:
		editor = os.getenv("VISUAL")
	if editor is None:
		editor = os.getenv("EDITOR")
	if editor is None:
		editor = "vi"
	cmd = [editor, proj.meta_path]
	os.execvp(editor, cmd)

def check(args):
	ctx = dbcontext.from_default_locations()
	prefix = args.prefix
	db = ctx.local_db(prefix)
	if args.fix:
		print("Canonicalizing project locations...")
		moved = db.canonicalize()
		if len(moved) > 0:
			print(f"{len(moved)} project(s) moved:")
			for old, new in moved:
				print(f"{old} -> {new}")
	issues = db.check()
	if len(issues) > 0:
		print(f"Found {len(issues)} issue(s):\n")
		for issue in issues:	
			print(":\n - ".join(issue) + "\n")
	else:
		print("Everything okay")

def remove(args):
	ctx = dbcontext.from_default_locations()
	prefix, name = rtokenize(args.project)
	try:
		db = ctx.local_db(prefix)
		proj = db[name]
		db.delete(name)
		print(f"Deleted project tree at {proj.path}")
		db.save()
	except Exception as e:
		prog_error(e, args)

def link(args):
	ctx = dbcontext.from_default_locations()
	prefix, name = rtokenize(args.project)
	try:
		proj = ctx.local_db(prefix)[name]
	except Exception as e:
		prog_error(e, args)
	if args.filename is None:
		filename = proj.name
	else:
		filename = args.filename
	os.symlink(proj.path, filename, target_is_directory=True)

def show_info(args):
	ctx = dbcontext.from_default_locations()
	site, host = tokenize(args.site)
	prefix, name = rtokenize(args.project)
	try:
		db = ctx.get_db(site, host, prefix)
	except Exception as e:
		prog_error(e, args)
	if name is None or len(name) == 0:
		path = ctx.get_prefix(site, prefix)
		if args.json:
			args.parser.error("argument --json: requires argument PROJECT")
		elif args.path:
			print(path)
		elif args.diff is not None:
			args.parser.error("argument --diff: requires argument PROJECT")
		else:
			print(f"{ctx.get_site(site).normalize_path_alias(prefix)}:{path}")
			print(f"#mtime# = {datetime.fromtimestamp(db.mtime()).isoformat()}")
			print(f"#size# = {format_bytes(db.size())}")
		return
	try:
		proj = db[name]
	except KeyError:
		prog_error(f"no match for '{name}'", args)
	if args.json:
		print(json.dumps(proj.to_dict(), indent=2))
	elif args.path:
		nodename = ""
		if host is not None:
			nodename = ctx.get_site(site).get_host(host) + ":"
		print(nodename + proj.path)
	elif args.diff is not None:
		site2, host2 = tokenize(args.diff)
		try:
			db2 = ctx.get_db(site2, host2, prefix)
		except KeyError as e:
			prog_error(e, args)
		try:
			proj2 = db2[proj.name]
		except KeyError:
			prog_error(f"no match for '{proj.name}'", args)
		diff = proj.diff(proj2)
		if diff is not None:
			print("".join(diff))
	else:
		print("".join(proj.format()))

def show_list(args):
	ctx = dbcontext.from_default_locations()
	site, host = tokenize(args.site)
	prefix, query = rtokenize(args.query)
	try:
		db = ctx.get_db(site, host, prefix)
	except Exception as e:
		prog_error(e, args)
	keys, reverse = parse_sort(args)
	projects = (db
		.subset(
			names=query, 
			scope=args.scope, 
			group=args.group)
		.sorted_by(
			*keys, 
			reverse=reverse)).projects
	if args.json:
		projects = [proj.to_dict() for proj in projects]
		print(json.dumps(projects, indent=2))
	elif args.long:
		print_proj_list(projects)
	elif args.path:
		nodename = ""
		if host is not None:
			nodename = ctx.get_site(site).get_host(host) + ":"
		for proj in projects:
			print(nodename + proj.path)
	else:
		for proj in projects:
			print(proj.name)

def search(args):
	ctx = dbcontext.from_default_locations()
	site, host = tokenize(args.site)
	prefix, query = rtokenize(args.query)
	try:
		db = ctx.get_db(site, host, prefix)
	except Exception as e:
		prog_error(str(e), args)
	keys, reverse = parse_sort(args)
	hitslist = (db
		.subset(
			scope=args.scope, 
			group=args.group)
		.sorted_by(
			*keys, 
			reverse=reverse)
		.search(
			pattern=query, 
			within=args.field,
			ignore_case=args.ignore_case))
	if args.json:
		hitslist = [asdict(hits) for hits in hitslist]
		print(json.dumps(hitslist, indent=2))
	elif args.path:
		nodename = ""
		if host is not None:
			nodename = ctx.get_site(site).get_host(host) + ":"
		for hits in hitslist:
			print(nodename + db[hits.name].path)
	else:
		print_search_list(hitslist, db)

def print_proj_list(plist, sep = "  "):
	if len(plist) > 0:
		path_len = max(len(proj.canonical_path) for proj in plist)
		size_len = 10
		time_len = 18
		for proj in plist:
			path = proj.canonical_path.ljust(path_len)
			size = format_bytes(proj.size).rjust(size_len)
			time = datetime.fromtimestamp(proj.mtime).strftime("%x %X").rjust(time_len)
			print(sep.join((path, size, time)))

def print_search_list(hlist, db, sep = ":  "):
	if len(hlist) > 0:
		for hits in hlist:
			proj = db[hits.name]
			print(proj.canonical_path + sep)
			pre_len = max(len(k) for k in hits.hits.keys())
			pre_len += len(sep)
			for k, v in hits.hits.items():
				pre = (k + sep).ljust(pre_len)
				match v:
					case str():
						print(pre + v)
					case list():
						for vj in v:
							print(pre + str(vj))
					case dict():
						for kj, vj in v.items():
							print(pre + kj + sep + str(vj))
			print()

