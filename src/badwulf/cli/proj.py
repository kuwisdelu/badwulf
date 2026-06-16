import os
import sys
import json
import shutil
import getpass
import subprocess
from datetime import date
from datetime import datetime
from datetime import timezone

from .site import load_sites
from .site import DEFAULT_PREFIX
from .site import DEFAULT_HOST

from ..db import projindex
from ..db import projdb
from ..util import prog_error
from ..util import format_bytes
from ..util import rtokenize
from ..util import mkpath
from ..util import mktree
from ..util import detect

INIT_SCOPE = "private"
INIT_GROUP = "scratch"

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

def create(args):
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
			prog_error(f"invalid prefix: {prefix}", args)
		path = os.path.join(sts.local.paths[prefix], 
			args.scope, args.group, name)
	db = projdb(sts.local.paths[prefix])
	if name in db:
		prog_error(f"project named '{name}' already exists", args)
	if not os.path.exists(path):
		mktree(path, force=True)
	p = os.path.join(path, "metadata.toml")
	with open(p, "w") as f:
		f.write("\n".join(template(args.scope, args.group, name)))
	print(f"Initialized project in {p}")

def link(args):
	sts = load_sites()
	prefix, name = rtokenize(args.project)
	if prefix is None:
		prefix = DEFAULT_PREFIX
	if prefix not in sts.local.paths:
		prog_error(f"invalid prefix: {prefix}", args)
	dbpath = sts.local.paths[prefix]
	db = projdb(dbpath)
	try:
		proj = db[name]
	except KeyError:
		prog_error(f"no project named {name}")
	if dbpath == os.path.commonpath((dbpath, os.getcwd())):
		path = os.path.join(
			os.path.relpath(dbpath, path), proj.canonical_path)
	else:
		path = proj.path
	filename = name if args.filename is None else args.filename
	cmd = ["ln", "-s", path, filename]
	subprocess.run(cmd)

def show(args):
	sts = load_sites()
	if args.query is None:
		prefix, name = DEFAULT_PREFIX, None
	else:
		prefix, name = rtokenize(args.query)
		if prefix is None:
			prefix = DEFAULT_PREFIX
		if prefix not in sts.local.paths:
			prog_error(f"invalid prefix: {prefix}", args)
	dbpath = sts.local.paths[prefix]
	db = projdb(dbpath)
	if len(args.sort) > 0:
		stat = args.sort
	elif len(args.reverse) > 0:
		stat = args.reverse
	else:
		stat = []
	stat.append("name")
	reverse = True if len(args.reverse) > 0 else False
	output = db.index.subset(
		names=name, 
		scope=args.scope, 
		group=args.group).sorted_by(*stat, reverse=reverse)
	if args.json:
		output = [proj.to_dict() for proj in output]
		print(json.dumps(output, indent=2))
	elif args.path:
		for proj in output:
			print(proj.path)
	else:
		if args.details:
			print_proj_list(output)
		else:
			for proj in output:
				print(proj.name)

def search(args):
	pass

def format_proj(proj):
	d = {
		"path": proj.canonical_path,
		"size": format_bytes(proj.size),
		"time": datetime.fromtimestamp(proj.mtime).strftime("%x %X"),
		"title": proj.meta.title}
	return d

def print_proj_list(plist, sep = "  "):
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
