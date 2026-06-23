import os
import sys
import json

from ..core import dbsyncer
from ..util import prog_error
from ..util import tokenize
from ..util import rtokenize
from ..util import mkpath
from ..util import mktree
from ..util import rmtree
from ..util import prune

def fetch(args):
	dbs = dbsyncer.from_default_locations()
	site, host = tokenize(args.site)
	prefix = args.prefix
	try:
		target  = (site, host, prefix)
		proc = dbs.pull_manifest(*target,
			dry_run=args.dry_run, 
			ask=args.ask)
	except Exception as e:
		prog_error(e, args)
	if proc.returncode != 0:
		print(f"Failed to fetch manifest from '{site}'")
	else:
		manifest_path = dbs.get_db(site, host, prefix).manifest
		print(f"Fetched manifest from '{site}' to {manifest_path}")

def pull(args):
	dbs = dbsyncer.from_default_locations()
	site, host = tokenize(args.site)
	prefix, name = rtokenize(args.project)
	try:
		target = (site, host, prefix)
		print(f"Copying manifest from '{site}'...")
		proc = dbs.pull_manifest(*target,
			dry_run=args.dry_run, 
			ask=args.ask)
	except Exception as e:
		prog_error(e, args)
	if proc.returncode != 0:
		prog_error(f"Failed to copy manifest from '{site}'", args)
	try:
		target  = (name, site, host, prefix)
		print(f"Syncing '{name}' project tree from '{site}'...")
		proc = dbs.pull_tree(*target,
			mirror=args.mirror,
			progress=args.progress,
			dry_run=args.dry_run,
			ask=args.ask)
	except Exception as e:
		prog_error(e, args)
	if proc.returncode != 0:
		prog_error(f"Failed to sync project tree from '{site}'", args)
	print(f"Transfer complete")

def push(args):
	dbs = dbsyncer.from_default_locations()
	site, host = tokenize(args.site)
	prefix, name = rtokenize(args.project)
	try:
		target  = (name, site, host, prefix)
		print(f"Syncing '{name}' project tree to '{site}'...")
		proc = dbs.push_tree(*target,
			mirror=args.mirror,
			progress=args.progress,
			dry_run=args.dry_run,
			ask=args.ask)
	except Exception as e:
		prog_error(e, args)
	if proc.returncode != 0:
		prog_error(f"Failed to sync project tree to '{site}'", args)
	try:
		target = (site, host, prefix)
		print(f"Copying manifest to '{site}'...")
		proc = dbs.push_manifest(*target,
			dry_run=args.dry_run,
			ask=args.ask)
	except Exception as e:
		prog_error(e, args)
	if proc.returncode != 0:
		prog_error(f"Failed to copy manifest to '{site}'", args)
	print(f"Transfer complete")

def status(args):
	sts = dbsyncer.from_default_locations()
	prog_error("NOT IMPLEMENTED YET", args)

