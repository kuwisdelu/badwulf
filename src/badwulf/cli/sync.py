import os
import sys
import json

from .site import load_sites
from .site import DEFAULT_SITE
from .site import DEFAULT_HOST
from .site import DEFAULT_PREFIX
from .proj import resolve_project

from ..db import projdb
from ..util import prog_error
from ..util import tokenize
from ..util import mkpath
from ..util import mktree
from ..util import prune

def resolve_site(args):
	sts = load_sites()
	if args.site is None:
		site, host = DEFAULT_SITE, None
	else:
		site, host = tokenize(args.site)
	if site not in sts:
		prog_error(f"unknown site: {site}", args)
	if host is None:
		if len(sts[site].hosts) > 0:
			host = DEFAULT_HOST
		else:
			host = None
	else:
		if host not in sts[site].hosts:
			prog_error(f"unknown host: {host}", args)
	return sts, site, host

def resolve_manifest(site = DEFAULT_SITE, host = None):
	if host is not None:
		return f"manifest-{site}-{host}.json"
	elif site != DEFAULT_SITE:
		return f"manifest-{site}.json"
	else:
		return f"manifest.json"

def fetch(args):
	sts, site, host = resolve_site(args)
	prefix = DEFAULT_PREFIX if args.prefix is None else args.prefix
	filename = resolve_manifest(site, host)
	dst = os.path.join(sts.local.paths[prefix], filename)
	sts.pull(
		site=site, 
		src=resolve_manifest(), 
		dst=dst,
		host_key=host,
		path_key=prefix,
		dry_run=args.dry_run,
		ask=args.ask)

def pull(args):
	sts = load_sites()
	prog_error("NOT IMPLEMENTED YET", args)

def push(args):
	sts = load_sites()
	prog_error("NOT IMPLEMENTED YET", args)

def status(args):
	sts = load_sites()
	prog_error("NOT IMPLEMENTED YET", args)

