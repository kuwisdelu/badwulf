from ..core import dbsyncer
from ..util import prog_error
from ..util import tokenize
from ..util import rtokenize

def fetch(args):
	dbs = dbsyncer.from_default_locations()
	site, host = tokenize(args.site)
	prefix = args.prefix
	try:
		target  = (site, host, prefix)
		proc = dbs.pull_manifest(*target,
			verbose=args.verbose,
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
			verbose=args.verbose,
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
			verbose=args.verbose,
			progress=args.progress,
			dry_run=args.dry_run,
			ask=args.ask)
	except Exception as e:
		prog_error(e, args)
	if proc.returncode != 0:
		prog_error(f"Failed to sync project tree from '{site}'", args)
	print("Transfer complete")

def push(args):
	dbs = dbsyncer.from_default_locations()
	site, host = tokenize(args.site)
	prefix, name = rtokenize(args.project)
	try:
		target  = (name, site, host, prefix)
		print(f"Syncing '{name}' project tree to '{site}'...")
		proc = dbs.push_tree(*target,
			mirror=args.mirror,
			verbose=args.verbose,
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
			verbose=args.verbose,
			dry_run=args.dry_run,
			ask=args.ask)
	except Exception as e:
		prog_error(e, args)
	if proc.returncode != 0:
		prog_error(f"Failed to copy manifest to '{site}'", args)
	print("Transfer complete")

def status(args):
	dbs = dbsyncer.from_default_locations()
	prefix = args.prefix
	local_db = dbs.local_db(prefix)
	print(f"{dbs.local_name}: {dbs.local_prefix(prefix)}\n")
	for k, v in dbs.sites.items():
		if k == dbs.local_name:
			continue
		else:
			try:
				v.get_path(prefix)
			except KeyError:
				continue
		if len(v.hosts) > 0:
			hosts = v.hosts.keys()
		else:
			hosts = [None]
		for h in hosts:
			print(f"{k}:" if h is None else f"{k}:{h}:")
			remote_db = dbs.get_db(k, h, prefix)
			add_db = remote_db.difference(local_db).sorted_by("name")
			for proj in add_db.projects:
				print(f"+{proj.name}")
			sub_db = local_db.difference(remote_db).sorted_by("name")
			for proj in sub_db.projects:
				print(f"-{proj.name}")
			if len(add_db) == 0 and len(sub_db) == 0:
				print("Everything synced")
			print("")
