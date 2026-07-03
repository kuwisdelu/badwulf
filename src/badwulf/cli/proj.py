
# Project management

import os
import json
import getpass
from datetime import date
from datetime import datetime
from dataclasses import asdict

from ..core import dbsyncer
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
	dbs = dbsyncer.from_default_locations()
	prefix, name = rtokenize(args.project)
	try:
		db = dbs.local_db(prefix)
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
	dbs = dbsyncer.from_default_locations()
	prefix, name = rtokenize(args.project)
	try:
		proj = dbs.local_db(prefix)[name]
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
	dbs = dbsyncer.from_default_locations()
	prefix = args.prefix
	db = dbs.local_db(prefix)
	if args.fix:
		print("Canonicalizing project locations...")
		moved = db.canonicalize()
		if len(moved) > 0:
			print(f"{len(moved)} project(s) moved:")
			for old, new in moved:
				print(f"{old} -> {new}")
	issues = db.check()
	if len(issues) > 0:
		print(f"{len(issues)} issue(s):")
		for k, v in issues:
			print(f"{k}: {v}")
	else:
		print("Everything okay")

def remove(args):
	dbs = dbsyncer.from_default_locations()
	prefix, name = rtokenize(args.project)
	try:
		db = dbs.local_db(prefix)
		proj = db[name]
		db.delete(name)
		print(f"Deleted project tree at {proj.path}")
		db.save()
	except Exception as e:
		prog_error(e, args)

def link(args):
	dbs = dbsyncer.from_default_locations()
	prefix, name = rtokenize(args.project)
	try:
		proj = dbs.local_db(prefix)[name]
	except Exception as e:
		prog_error(e, args)
	if args.filename is None:
		filename = proj.name
	else:
		filename = args.filename
	os.symlink(proj.path, filename, target_is_directory=True)

def show_info(args):
	dbs = dbsyncer.from_default_locations()
	site, host = tokenize(args.site)
	prefix, name = rtokenize(args.project)
	try:
		db = dbs.get_db(site, host, prefix)
	except Exception as e:
		prog_error(e, args)
	try:
		proj = db[name]
	except KeyError:
		prog_error(f"no match for '{name}' at '{args.site}'", args)
	if args.json:
		print(json.dumps(proj.to_dict(), indent=2))
	elif args.path:
		nodename = ""
		if host is not None:
			nodename = dbs.get_site(site).get_host(host) + ":"
		print(nodename + proj.path)
	elif args.diff is not None:
		site2, host2 = tokenize(args.diff)
		try:
			db2 = dbs.get_db(site2, host2, prefix)
		except KeyError as e:
			prog_error(e, args)
		try:
			proj2 = db2[proj.name]
		except KeyError:
			prog_error(f"no match for '{proj.name}' at '{args.diff}'", args)
		diff = proj.diff(proj2)
		if diff is not None:
			print("".join(diff))
	else:
		print("".join(proj.format()))

def show_list(args):
	dbs = dbsyncer.from_default_locations()
	site, host = tokenize(args.site)
	prefix, query = rtokenize(args.query)
	try:
		db = dbs.get_db(site, host, prefix)
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
			nodename = dbs.get_site(site).get_host(host) + ":"
		for proj in projects:
			print(nodename + proj.path)
	else:
		for proj in projects:
			print(proj.name)

def search(args):
	dbs = dbsyncer.from_default_locations()
	site, host = tokenize(args.site)
	prefix, query = rtokenize(args.query)
	try:
		db = dbs.get_db(site, host, prefix)
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
			nodename = dbs.get_site(site).get_host(host) + ":"
		for hits in hitslist:
			print(nodename + db[hits.name].path)
	else:
		print_search_list(hitslist)

def format_proj(proj):
	return {
		"path": proj.canonical_path,
		"size": format_bytes(proj.size),
		"time": datetime.fromtimestamp(proj.mtime).strftime("%x %X"),
		"title": proj.meta.title}

def print_proj_list(plist, sep = "  "):
	if len(plist) > 0:
		dlist = [format_proj(proj) for proj in plist]
		path_len = max(len(d["path"]) for d in dlist)
		size_len = max(len(d["size"]) for d in dlist)
		time_len = max(len(d["time"]) for d in dlist)
		for d in dlist:
			sl = []
			sl.append(d["path"].ljust(path_len))
			sl.append(d["size"].rjust(size_len))
			sl.append(d["time"].rjust(time_len))
			sl.append(d["title"])
			print(sep.join(sl))

def format_search(proj):
	hits = []
	for field, hit in proj.hits.items():
		ctx = [proj.name, field]
		match hit:
			case str():
				hits.append({"ctx": ctx, "hit": hit})
			case list():
				for subhit in hit:
					match subhit:
						case str():
							hits.append({"ctx": ctx, "hit": hit})
						case dict():
							for k, v in subhit.items():
								hits.append({"ctx": ctx + [k], "hit": v})
			case dict():
				for k, v in hit.items():
					hits.append({"ctx": ctx + [k], "hit": v})
	return hits

def print_search_list(plist, sep = ":  "):
	if len(plist) > 0:
		hlist = []
		for proj in plist:
			hlist.extend(format_search(proj))
		name_len = max(len(hit["ctx"][0]) for hit in hlist)
		name_len += len(sep)
		ctx_len = max(len(sep.join(hit["ctx"][1:])) for hit in hlist)
		ctx_len += len(sep)
		for hit in hlist:
			name = (hit["ctx"][0] + sep).ljust(name_len)
			ctx = (sep.join(hit["ctx"][1:]) + sep).ljust(ctx_len)
			print(f'{name}{ctx}{hit["hit"]}')

