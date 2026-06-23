import argparse
import getpass
from importlib import metadata

from . import site
from . import proj
from . import sync

SITE_METAVAR = "SITE[:HOST]"
PROJ_METAVAR = "[PREFIX:]PROJECT"
QUERY_METAVAR = "[PREFIX:]QUERY"

def main():
	args = build_parser().parse_args()
	args.func(args)

def build_parser():
	p = argparse.ArgumentParser(prog="wulf")
	p.set_defaults(func=lambda args: p.print_help())
	p.add_argument("-v", "--version", 
		help="show version and exit",
		action="version",
		version=f"badwulf {metadata.version("badwulf")}")
	sub = p.add_subparsers(metavar="command")
	# create and query projects
	register_add(sub)
	register_edit(sub)
	register_check(sub)
	register_remove(sub)
	register_link(sub)
	register_list(sub)
	register_search(sub)
	# sync and compare projects
	register_fetch(sub)
	register_pull(sub)
	register_push(sub)
	register_status(sub)
	# configure work sites
	register_site(sub)
	register_run(sub)
	return p

def _add_project(p, opt=False):
	help_text = "project specification"
	nargs = "?" if opt else None
	p.add_argument("project", 
		help=help_text,
		metavar=PROJ_METAVAR,
		nargs=nargs)

def _add_prefix(p, opt=False):
	help_text = "database prefix"
	nargs = "?" if opt else None
	p.add_argument("prefix", 
		help=help_text,
		metavar="PREFIX",
		nargs=nargs)

def _add_site(p, opt=False):
	help_text = "site specification"
	nargs = "?" if opt else None
	p.add_argument("site", 
		help=help_text,
		metavar=SITE_METAVAR,
		nargs=nargs)

def _add_site_option(p):
	help_text = "site specification"
	help_text += f" (if not local)"
	p.add_argument("-S", "--site", 
		help=help_text,
		metavar=SITE_METAVAR)

def _add_scope_filter(p):
	p.add_argument("-s", "--scope", 
		help="filter by scope",
		action="append")

def _add_group_filter(p):
	p.add_argument("-g", "--group", 
		help="filter by group",
		action="append")

def _add_dry_run(p):
	p.add_argument("-n", "--dry-run", 
		help="simulate actions without applying changes?",
		action="store_true")

def _add_verbose(p):
	p.add_argument("-v", "--verbose", 
		help="show verbose output",
		action="store_true")

def _add_mirror(p):
	p.add_argument("--mirror", 
		help="delete files on destination that aren't in source?",
		action="store_true")

def _add_no_progress(p):
	p.add_argument("--no-progress", 
		help="no partial progress",
		action="store_false",
		dest="progress")

def _add_ask(p):
	p.add_argument("--ask", 
		help="ask for confirmation?",
		action="store_true")

def _add_path(p):
	p.add_argument("--path",
		help="path output",
		action="store_true")

def _add_json(p):
	p.add_argument("--json", 
		help="json output",
		action="store_true")

def _add_sort_group(p):
	g = p.add_mutually_exclusive_group()
	g.add_argument("-r", "--reverse", 
		choices=["name", "size", "mtime"],
		help="sort by project statistics (descending)",
		action="append",
		default=[])
	g.add_argument("--sort", 
		choices=["name", "size", "mtime"],
		help="sort by project statistics (ascending)",
		action="append",
		default=[])

def _add_filter_group(p):
	_add_scope_filter(p)
	_add_group_filter(p)

def _add_sync_group(p):
	_add_site(p)
	_add_project(p)
	_add_verbose(p)
	_add_dry_run(p)
	_add_no_progress(p)
	_add_mirror(p)
	_add_ask(p)

def register_add(subparsers):
	p = subparsers.add_parser("add", 
		help="Create an empty project",
		aliases=["init"])
	p.set_defaults(func=proj.add, parser=p)
	_add_project(p)
	p.add_argument("-s", "--scope", 
		help=f"project scope (default: {proj.DEFAULT_SCOPE})",
		default=proj.DEFAULT_SCOPE)
	p.add_argument("-g", "--group", 
		help=f"project group (default: {proj.DEFAULT_GROUP})",
		default=proj.DEFAULT_GROUP)

def register_edit(subparsers):
	p = subparsers.add_parser("edit", 
		help="Edit project metadata")
	p.set_defaults(func=proj.edit, parser=p)
	_add_project(p)
	p.add_argument("-E", "--editor",
		help="text editor to use")

def register_check(subparsers):
	p = subparsers.add_parser("check", 
		help="Check for issues")
	p.set_defaults(func=proj.check, parser=p)
	_add_prefix(p, opt=True)
	p.add_argument("--fix",
		help="fix issues where possible",
		action="store_true")

def register_remove(subparsers):
	p = subparsers.add_parser("remove",
		help="Delete a project",
		aliases=["rm"])
	p.set_defaults(func=proj.remove, parser=p)
	_add_project(p)

def register_link(subparsers):
	p = subparsers.add_parser("link", 
		help="Create a symlink to a project",
		aliases=["ln"])
	p.set_defaults(func=proj.link, parser=p)
	_add_project(p)
	p.add_argument("filename", 
		help="symlink filename",
		metavar="FILENAME",
		nargs="?")

def register_list(subparsers):
	p = subparsers.add_parser("list", 
		help="List projects",
		aliases=["ls"])
	g = p.add_mutually_exclusive_group()
	p.set_defaults(func=proj.show, parser=p)
	p.add_argument("query",
		help="pattern (over project names)",
		metavar=QUERY_METAVAR,
		nargs="?")
	p.add_argument("-l", "--long", 
		help="show details",
		action="store_true")
	_add_site_option(p)
	_add_filter_group(p)
	_add_sort_group(p)
	_add_path(g)
	_add_json(g)

def register_search(subparsers):
	p = subparsers.add_parser("search", 
		help="Search project metadata",
		aliases=["grep"])
	g = p.add_mutually_exclusive_group()
	p.set_defaults(func=proj.search, parser=p)
	p.add_argument("query",
		help="pattern (over project metadata)",
		metavar=QUERY_METAVAR)
	_add_site_option(p)
	_add_filter_group(p)
	p.add_argument("-f", "--field",
		help="metadata fields to search",
		action="append")
	p.add_argument("-i", "--ignore-case",
		help="ignore case",
		action="store_true")
	_add_sort_group(p)
	_add_path(g)
	_add_json(g)

def register_fetch(subparsers):
	p = subparsers.add_parser("fetch", 
		help="Get manifest of projects from another site")
	p.set_defaults(func=sync.fetch, parser=p)
	_add_site(p)
	_add_prefix(p, opt=True)
	_add_verbose(p)
	_add_dry_run(p)
	_add_ask(p)

def register_pull(subparsers):
	p = subparsers.add_parser("pull", 
		help="Download a project from another site")
	p.set_defaults(func=sync.pull, parser=p)
	_add_sync_group(p)

def register_push(subparsers):
	p = subparsers.add_parser("push", 
		help="Upload a project to another site")
	p.set_defaults(func=sync.push, parser=p)
	_add_sync_group(p)

def register_status(subparsers):
	p = subparsers.add_parser("status", 
		help="Get status of projects across sites")
	p.set_defaults(func=sync.status, parser=p)
	_add_prefix(p, opt=True)

def register_site(subparsers):
	p = subparsers.add_parser("site", 
		help="Configure work sites",
		aliases=["remote"])
	g = p.add_mutually_exclusive_group()
	p.set_defaults(func=site.main, parser=p)
	p.add_argument("subcommand",
		help="Add, get, set, or remove site configuration",
		choices=["add", "get", "set", "unset", "remove"],
		nargs="?")
	p.add_argument("name",
		help="Site name",
		metavar="NAME",
		nargs="?")
	_add_verbose(g)
	p.add_argument("--user", 
		help="site user",
		nargs="?",
		default=False)
	p.add_argument("--host", 
		help="site HOST(s) as <alias>:<host>",
		action="append",
		nargs="?",
		default=[])
	p.add_argument("--path", 
		help="site PREFIX(es) as <alias>:<path>",
		action="append",
		nargs="?",
		default=[])
	p.add_argument("--proxy-user", 
		help="site proxy jump user",
		nargs="?",
		default=False)
	p.add_argument("--proxy-host", 
		help="site proxy jump host",
		nargs="?",
		default=False)
	_add_json(g)

def register_run(subparsers):
	p = subparsers.add_parser("run", 
		help="Run a shell command at another site")
	p.set_defaults(func=site.run, parser=p)
	_add_site(p)
	p.add_argument("command",
		help="command to run",
		metavar="COMMAND",
		nargs="*")
