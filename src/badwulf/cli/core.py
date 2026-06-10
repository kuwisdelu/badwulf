
# Core command line interface tools

import os

from ..sync import syncer
from ..util import mkpath

def detect_sites(p = "badwulf-sites.json"):
	if "BADWULF_SITES" in os.environ:
		return mkpath("$BADWULF_SITES")
	dp = "." + p
	if os.path.exists(p):
		return mkpath(p)
	if os.path.exists(mkpath(dp)):
		return mkpath(mkpath(dp))
	if os.path.exists(mkpath("$HOME", ".badwulf")):
		prefix = ("$HOME", ".badwulf")
	else:
		prefix = ("$HOME",)
	if os.path.exists(mkpath(*prefix, p)):
		return mkpath(mkpath(*prefix, p))
	if os.path.exists(mkpath(*prefix, dp)):
		return mkpath(mkpath(*prefix, dp))
	raise FileNotFoundError(f"couldn't find '{p}'")

def cmd_init(args):
	print("hello, world!")
