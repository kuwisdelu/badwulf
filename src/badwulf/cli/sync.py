import os
import sys
import json

from .site import load_sites
from .site import DEFAULT_SITE
from .site import DEFAULT_HOST
from .site import DEFAULT_PREFIX

from ..db import projindex
from ..db import projdb
from ..util import prog_error
from ..util import tokenize
from ..util import mkpath
from ..util import mktree
from ..util import prune

def fetch(args):
	sts = load_sites()
	prog_error("NOT IMPLEMENTED YET", args)

def pull(args):
	sts = load_sites()
	prog_error("NOT IMPLEMENTED YET", args)

def push(args):
	sts = load_sites()
	prog_error("NOT IMPLEMENTED YET", args)

def status(args):
	sts = load_sites()
	prog_error("NOT IMPLEMENTED YET", args)

def parse_site(args):
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
