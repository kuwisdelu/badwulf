import os
import sys
import json

from ..db import projdb
from ..util import prog_error
from ..util import tokenize
from ..util import mkpath
from ..util import mktree
from ..util import rmtree
from ..util import prune

def fetch(args):
	if proc.returncode != 0:
		print(f"Failed to fetch manifest from {site}")
		if os.path.isdir(manifest_path):
			rmtree(manifest_path)
			print(f"Removed temporary {manifest_path}")
	else:
		print(f"Fetched manifest from {site} to {manifest_path}")

def pull(args):
	sts = dbsyncer.from_default_locations()
	prog_error("NOT IMPLEMENTED YET", args)

def push(args):
	pass
	# sts = dbsyncer.from_default_locations()
	# sts, site, host = resolve_site(args)
	# db, prefix, proj = resolve_project(args)
	# manifest = resolve_manifest(site, host)
	# manifest_path = os.path.join(sts.local.paths[prefix], manifest)
	# print(f"Fetching manifest from {site}")
	# proc = sts.pull(
	# 	site=site, 
	# 	src=resolve_manifest(), 
	# 	dst=manifest,
	# 	host_key=host,
	# 	path_key=prefix)
	# if proc.returncode != 0:
	# 	print(f"Failed to fetch manifest from {site}")
	# 	if os.path.isdir(manifest_path):
	# 		rmtree(manifest_path)
	# 		print(f"Removed temporary {manifest_path}")
	# 	remote_db = projdb([proj], manifest=manifest_path)
	# 	remote_db.save()
	# else:
	# 	print(f"Fetched manifest from {site} to {manifest_path}")
	# 	remote_db = projdb(manifest=manifest_path)
	# 	prog_error("NOT IMPLEMENTED YET", args)
	# print(f"Sending manifest to {site}...")
	# proc = sts.push(
	# 	site=site, 
	# 	src=manifest, 
	# 	dst=resolve_manifest(),
	# 	host_key=host,
	# 	path_key=prefix)
	# if proc.returncode != 0:
	# 	print(f"Failed to send manifest to {site}")
	# print(f"Syncing project tree for '{proj.name}' to {site}...")
	# proc = sts.push(
	# 	site=site,
	# 	src=proj.path,
	# 	dst=proj.canonical_path,
	# 	isdir=True,
	# 	host_key=host,
	# 	path_key=prefix,
	# 	mirror=args.mirror,
	# 	progress=True,
	# 	dry_run=args.dry_run,
	# 	ask=args.ask)
	# if proc.returncode != 0:
	# 	print(f"Failed to push to {site}")
	# else:
	# 	print(f"Pushed '{proj.name}' to {site}")

def status(args):
	sts = dbsyncer.from_default_locations()
	prog_error("NOT IMPLEMENTED YET", args)

