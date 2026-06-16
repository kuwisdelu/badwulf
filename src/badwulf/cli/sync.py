import os
import sys
import json

from .site import load_sites
from .site import DEFAULT_SITE
from .site import DEFAULT_HOST
from .site import DEFAULT_PREFIX

from ..sync import profile
from ..sync import syncer
from ..util import prog_error
from ..util import tokenize
from ..util import mkpath
from ..util import mktree
from ..util import detect
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
