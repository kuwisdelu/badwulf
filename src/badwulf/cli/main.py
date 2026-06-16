import os
import sys
import json
import argparse
from importlib import metadata

from . import site
from . import proj

SITE_METAVAR = "SITE[:HOST]"
PROJ_METAVAR = "[PREFIX:]NAME"
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
	# create and explore projects
	register_init(sub)
	register_link(sub)
	register_list(sub)
	register_find(sub)
	# sync and compare projects
	register_fetch(sub)
	register_pull(sub)
	register_push(sub)
	register_remove(sub)
	register_status(sub)
	# configure work sites
	register_site(sub)
	register_run(sub)
	return p

def _add_project(p, opt=False, cwd=False):
	help_text = "project specification"
	if cwd:
		help_text += " (if not current directory)"
	nargs = "?" if opt else None
	p.add_argument("project", 
		help=help_text,
		metavar=PROJ_METAVAR,
		nargs=nargs)

def _add_prefix(p, opt=False, cwd=False):
	help_text = "database prefix"
	if cwd:
		help_text += f" (if not '{site.DEFAULT_PREFIX}')"
	nargs = "?" if opt else None
	p.add_argument("prefix", 
		help=help_text,
		metavar="PREFIX",
		nargs=nargs)

def _add_site(p, opt=False):
	help_text = "target site specification"
	nargs = "?" if opt else None
	p.add_argument("site", 
		help=help_text,
		metavar=SITE_METAVAR,
		nargs=nargs)

def _add_site_option(p):
	help_text = "site specification"
	help_text += f" (if not '{site.DEFAULT_SITE}')"
	p.add_argument("-t", "--site", 
		help=help_text,
		metavar=SITE_METAVAR)

def _add_details(p):
	p.add_argument("-l", "--details", 
		help="show details",
		action="store_true")

def _add_scope_filter(p):
	p.add_argument("-s", "--scope", 
		help="filter by scope",
		action="append")

def _add_group_filter(p):
	p.add_argument("-g", "--group", 
		help="filter by group",
		action="append")

def _add_force(p):
	p.add_argument("-f", "--force", 
		help="force transfer even if rejected?",
		action="store_true")

def _add_dry_run(p):
	p.add_argument("-n", "--dry-run", 
		help="show what would happen without doing it?",
		action="store_true")

def _add_ask(p):
	p.add_argument("-a", "--ask", 
		help="ask confirmation before performing the operation?",
		action="store_true")

def _add_json(p):
	p.add_argument("--json", 
		help="json output",
		action="store_true")

def _add_sort_group(p):
	g = p.add_mutually_exclusive_group()
	g.add_argument("-r", "--reverse", 
		choices=["size", "mtime", "atime"],
		help="sort by project statistics (descending)",
		action="append",
		default=[])
	g.add_argument("--sort", 
		choices=["size", "mtime", "atime"],
		help="sort by project statistics (ascending)",
		action="append",
		default=[])

def _add_query_group(p):
	_add_scope_filter(p)
	_add_group_filter(p)
	_add_sort_group(p)

def _add_sync_group(p):
	_add_site(p)
	_add_project(p, opt=True, cwd=True)
	_add_force(p)
	_add_dry_run(p)
	_add_ask(p)

def register_init(subparsers):
	p = subparsers.add_parser("init", 
		help="Create an empty project")
	p.set_defaults(func=proj.create, parser=p)
	_add_project(p, opt=True, cwd=True)
	p.add_argument("-s", "--scope", 
		help=f"project scope (default: {proj.INIT_SCOPE})",
		action="store",
		default=proj.INIT_SCOPE)
	p.add_argument("-g", "--group", 
		help=f"project group (default: {proj.INIT_GROUP})",
		action="store",
		default=proj.INIT_GROUP)

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
	_add_details(g)
	g.add_argument("-p", "--path",
		help="show path",
		action="store_true")
	_add_site_option(p)
	_add_query_group(p)
	_add_json(g)

def register_find(subparsers):
	p = subparsers.add_parser("find", 
		help="Search project metadata",
		aliases=["grep"])
	g = p.add_mutually_exclusive_group()
	p.set_defaults(func=lambda args: print(args), parser=p)
	p.add_argument("query",
		help="pattern (over project metadata)",
		metavar=QUERY_METAVAR)
	_add_details(g)
	_add_site_option(p)
	p.add_argument("-w", "--within",
		help="metadata fields to search",
		action="append")
	p.add_argument("-i", "--ignore-case",
		help="ignore case",
		action="store_true")
	_add_query_group(p)
	_add_json(g)

def register_fetch(subparsers):
	p = subparsers.add_parser("fetch", 
		help="Get manifest of projects from another site")
	p.set_defaults(func=lambda args: print(args), parser=p)
	_add_site(p)
	_add_prefix(p, opt=True, cwd=True)
	_add_dry_run(p)
	_add_ask(p)

def register_pull(subparsers):
	p = subparsers.add_parser("pull", 
		help="Download a project from another site")
	p.set_defaults(func=lambda args: print(args), parser=p)
	_add_sync_group(p)

def register_push(subparsers):
	p = subparsers.add_parser("push", 
		help="Upload a project to another site")
	p.set_defaults(func=lambda args: print(args), parser=p)
	_add_sync_group(p)

def register_remove(subparsers):
	p = subparsers.add_parser("remove",
		help="Delete a project",
		aliases=["rm"])
	p.set_defaults(func=lambda args: print(args), parser=p)
	_add_project(p)
	_add_ask(p)

def register_status(subparsers):
	p = subparsers.add_parser("status", 
		help="Get status of tracked projects")
	p.set_defaults(func=lambda args: print(args), parser=p)
	_add_prefix(p, opt=True, cwd=True)
	p.add_argument("-c", "--clean",
		help="clean up project directories",
		action="store_true")
	_add_json(p)

def register_site(subparsers):
	p = subparsers.add_parser("site", 
		help="Configure work sites")
	g = p.add_mutually_exclusive_group()
	p.set_defaults(func=site.main, parser=p)
	p.add_argument("subcommand",
		help="Add, get, set, or remove site configuration",
		choices=["add", "get", "set", "unset", "remove"],
		nargs="?")
	p.add_argument("name",
		help="Site name",
		metavar="NAME",
		nargs="?",
		default=site.DEFAULT_SITE)
	g.add_argument("-v", "--verbose", 
		help="verbose output",
		action="store_true")
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
	p.set_defaults(func=lambda args: print(args), parser=p)
	_add_site(p)
	p.add_argument("command",
		help="command to run",
		metavar="COMMAND",
		nargs="?")
