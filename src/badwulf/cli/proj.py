import os
import sys
import json
import getpass
from datetime import date

from .site import load_sites
from .site import DEFAULT_PATH
from .site import DEFAULT_HOST
from ..db import projindex
from ..db import projdb
from ..util import prog_error
from ..util import rtokenize
from ..util import mkpath
from ..util import mktree
from ..util import detect

DEFAULT_SCOPE = "local"
DEFAULT_GROUP = "scratch"

def detect_prefix():
	cfg = load_sites()
	current = os.getcwd()
	paths = cfg.sites[cfg.local].paths.items()
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

def metadata(scope, group, name):
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
			prog_error("project not under a known prefix", args)
		name = os.path.basename(os.getcwd())
		path = os.getcwd()
	else:
		prefix, name = rtokenize(args.project)
		if prefix is None:
			prefix = DEFAULT_PATH
		cfg = load_sites()
		dbpath = cfg.sites[cfg.local].paths.get(prefix)
		if dbpath is None:
			prog_error(f"invalid prefix: {prefix}", args)
		path = os.path.join(dbpath, args.scope, args.group, name)
	if name in projdb(dbpath):
		prog_error(f"project named '{name}' already exists", args)
	if not os.path.exists(path):
		mktree(path, force=True)
	p = os.path.join(path, "metadata.toml")
	with open(p, "w") as f:
		f.write("\n".join(metadata(args.scope, args.group, name)))
	print(f"Initialized project in {p}")

def link(args):
	pass

def show(args):
	pass

def search(args):
	pass
