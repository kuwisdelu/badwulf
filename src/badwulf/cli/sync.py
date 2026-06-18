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
		site, host = DEFAULT_SITE, DEFAULT_HOST
	else:
		site, host = tokenize(args.site)
		if host is None:
			host = DEFAULT_HOST
	if site not in sts:
		prog_error(f"unknown site: {site}", args)
	return sts, site, host

def fetch(args):
	sts, site, host = resolve_site(args)
	prefix = DEFAULT_PREFIX if args.prefix is None else args.prefix
	filename = f"manifest-{site}-{host}.json"
	dst = os.path.join(sts[site].paths[prefix], filename)
	sts.pull(site, 
		src="manifest.json", 
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

