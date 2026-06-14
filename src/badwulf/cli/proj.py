import os
import sys
import json
import getpass
import subprocess
from datetime import date

from .site import load_sites
from .site import DEFAULT_PREFIX
from .site import DEFAULT_NODE

from ..db import projindex
from ..db import projdb
from ..util import prog_error
from ..util import rtokenize
from ..util import mkpath
from ..util import mktree
from ..util import detect

INIT_SCOPE = "local"
INIT_GROUP = getpass.getuser()

def detect_prefix():
	sts = load_sites()
	current = os.getcwd()
	paths = sts.local.paths.items()
	paths = {k: mkpath(v) for k, v in paths}
	for k, v in paths:
		if v == os.path.commonpath((v, current)):
			return k, v
	return None, None

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

def relative_prefix(prefix):
	prefix = mkpath(prefix)
	current = ""
	parent = os.path.dirname(mkpath(current))
	while not os.path.samefile(mkpath(current), parent):
		if os.path.samefile(mkpath(current), prefix):
			return current
		current = os.path.join(current, "..")
		parent = os.path.dirname(mkpath(current))
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
	return fields

def create(args):
	if args.project is None:
		if detect_project() is not None:
			prog_error("project is already initialized", args)
		prefix, dbpath = detect_prefix()
		if prefix is None:
			prog_error("project is not under a known prefix", args)
		name = os.path.basename(os.getcwd())
		path = os.getcwd()
	else:
		prefix, name = rtokenize(args.project)
		if prefix is None:
			prefix = DEFAULT_PREFIX
		sts = load_sites()
		dbpath = sts.local.paths.get(prefix)
		if dbpath is None:
			prog_error(f"invalid prefix: {prefix}", args)
		path = os.path.join(dbpath, args.scope, args.group, name)
	if name in projdb(dbpath):
		prog_error(f"project named '{name}' already exists", args)
	if not os.path.exists(path):
		mktree(path, force=True)
	p = os.path.join(path, "metadata.toml")
	with open(p, "w") as f:
		f.write("\n".join(template(args.scope, args.group, name)))
	print(f"Initialized project in {p}")

def symlink(args):
	sts = load_sites()
	prefix, name = rtokenize(args.project)
	if prefix is None:
		prefix = DEFAULT_PREFIX
	dbpath = sts.local.paths.get(prefix)
	if dbpath is None:
		prog_error(f"invalid prefix: {prefix}", args)
	db = projdb(dbpath)
	proj = db.get(name)
	if proj is None:
		prog_error(f"no project named {name}")
	if dbpath == os.path.commonpath((dbpath, os.getcwd())):
		if proj.is_misplaced_relative(dbpath):
			path = proj.path
		else:
			path = os.path.join(
				relative_prefix(dbpath), proj.canonical_path)
	else:
		path = proj.path
	filename = name if args.filename is None else args.filename
	cmd = ["ln", "-s", path, filename]
	subprocess.run(cmd)

def show(args):
	pass

def search(args):
	pass
