import os
import json
import tomllib
import getpass
from datetime import date
from datetime import datetime
from datetime import timezone
from dataclasses import asdict

from .site import load_sites
from .site import resolve_site
from .site import resolve_manifest
from .site import DEFAULT_SITE
from .site import DEFAULT_HOST
from .site import DEFAULT_PREFIX

from ..db import projdb
from ..util import prog_error
from ..util import format_bytes
from ..util import rtokenize
from ..util import mkpath
from ..util import mktree
from ..util import detect

DEFAULT_SCOPE = "private"
DEFAULT_GROUP = "scratch"

def detect_project():
	current = os.getcwd()
	parent = os.path.dirname(current)
	while not os.path.samefile(current, parent):
		try:
			path = detect(r"^metadata\.toml$", current)
			return os.path.dirname(path)
		except FileNotFoundError:
			current = parent
			parent = os.path.dirname(current)
	return None

def resolve_query(args, sts = None):
	sts, site, host = resolve_site(args, sts)
	if args.query is None:
		prefix, query = DEFAULT_PREFIX, None
	else:
		prefix, query = rtokenize(args.query)
		if prefix is None:
			prefix = DEFAULT_PREFIX
		if prefix not in sts[site].paths:
			prog_error(f"unknown prefix: {prefix}", args)
	if sts[site] == sts.local:
		db = projdb(root=sts[site].paths[prefix])
	else:
		manifest = resolve_manifest(site, host)
		manifest_path = os.path.join(sts.local.paths[prefix], manifest)
		db = projdb(manifest=manifest_path)
	return db, prefix, query

def resolve_project(args, sts = None):
	if sts is None:
		sts = load_sites()
	if args.project is None:
		path = detect_project()
		if path is None:
			prog_error("working directory is not a project")
		try:
			prefix = sts.local.resolve_prefix(path)
			db = projdb(root=sts.local.paths[prefix])
			proj = db.find(path)
		except ValueError:
			prog_error(f"no known project tracked at {path}", args)
	else:
		prefix, name = rtokenize(args.project)
		if prefix is None:
			prefix = DEFAULT_PREFIX
		if prefix not in sts.local.paths:
			prog_error(f"unknown prefix: {prefix}", args)
		db = projdb(root=sts.local.paths[prefix])
		try:
			proj = db[name]
		except KeyError:
			prog_error(f"no project named {name}", args)
	return db, prefix, proj

def template(scope, group, name):
	fields = []
	fields.append(f'name = "{name}"')
	fields.append(f'scope = "{scope}"')
	fields.append(f'group = "{group}"')
	fields.append(f'title = "{name}"')
	fields.append(f'date.created = {date.today().isoformat()}')
	fields.append(f'keywords = []')
	fields.append(f'formats = []')
	fields.append(f'contact = [{{name = "{getpass.getuser()}"}}]')
	fields.append(f'description.abstract = ""')
	fields.append("")
	return fields

def add(args):
	sts = load_sites()
	if args.project is None:
		if detect_project() is not None:
			prog_error("project is already initialized", args)
		try:
			prefix = sts.local.detect_prefix()
		except ValueError:
			prog_error("project is not under a known prefix", args)
		name = os.path.basename(os.getcwd())
		path = os.getcwd()
	else:
		prefix, name = rtokenize(args.project)
		if prefix is None:
			prefix = DEFAULT_PREFIX
		if prefix not in sts.local.paths:
			prog_error(f"unknown prefix: {prefix}", args)
		path = os.path.join(sts.local.paths[prefix], 
			args.scope, args.group, name)
	db = projdb(root=sts.local.paths[prefix])
	if name in db:
		prog_error(f"project named '{name}' already exists", args)
	if not os.path.exists(path):
		mktree(path, force=True)
		print(f"Created project tree at {path}")
	p = os.path.join(path, "metadata.toml")
	with open(p, "w") as f:
		f.write("\n".join(template(args.scope, args.group, name)))
	print(f"Initialized {p}")

def edit(args):
	db, prefix, proj = resolve_project(args)
	filename = os.path.join(proj.path, "metadata.toml")
	editor = args.editor
	if editor is None:
		editor = os.getenv("VISUAL")
	if editor is None:
		editor = os.getenv("EDITOR")
	if editor is None:
		editor = "vi"
	cmd = [editor, filename]
	os.execvp(editor, cmd)

def remove(args):
	db, prefix, proj = resolve_project(args)
	path = proj.path
	proj.unlink()
	print(f"Deleted project tree at {path}")

def link(args):
	db, prefix, proj = resolve_project(args)
	filename = proj.name if args.filename is None else args.filename
	os.symlink(proj.path, filename, target_is_directory=True)

def show(args):
	db, prefix, query = resolve_query(args)
	keys, reverse = parse_sort(args)
	outlist = (db
		.subset(
			names=query, 
			scope=args.scope, 
			group=args.group)
		.sorted_by(
			*keys, 
			reverse=reverse)).projects
	if args.json:
		outlist = [proj.to_dict() for proj in outlist]
		print(json.dumps(outlist, indent=2))
	elif args.long:
		print_proj_list(outlist)
	elif args.path:
		for proj in outlist:
			print(proj.path)
	else:
		for proj in outlist:
			print(proj.name)

def search(args):
	db, prefix, query = resolve_query(args)
	keys, reverse = parse_sort(args)
	outlist = (db
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
		outlist = [asdict(hits) for hits in outlist]
		print(json.dumps(outlist, indent=2))
	elif args.path:
		for hits in outlist:
			print(db[hits.name].path)
	else:
		print_search_list(outlist)

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
			print(f"{name}{ctx}{hit["hit"]}")
