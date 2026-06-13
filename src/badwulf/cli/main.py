import os
import sys
import json
import argparse
from importlib import metadata

from . import site
from . import proj

SITE_HINT = "SITE[:NODE]"
PROJECT_HINT = "[PREFIX:]NAME"
SEARCH_HINT = "[PREFIX:]QUERY"

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
	register_clone(sub)
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
		help_text = help_text + " (if not current directory)"
	nargs = "?" if opt else 1
	p.add_argument("project", 
		help=help_text,
		metavar=PROJECT_HINT,
		nargs=nargs)

def _add_site(p, opt=False):
	help_text = "site specification"
	if opt:
		p.add_argument("site", 
			help=help_text,
			metavar=SITE_HINT,
			nargs="?",
			default=site.DEFAULT_SITE)
	else:
		p.add_argument("site", 
			help=help_text,
			metavar=SITE_HINT)

def _add_site_opt(p):
	p.add_argument("-t", "--site", 
		help="site specification",
		metavar=SITE_HINT,
		default=site.DEFAULT_SITE)

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
	p.add_argument("-j", "--json", 
		help="json output",
		action="store_true")

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
	return p

def register_clone(subparsers):
	p = subparsers.add_parser("clone", 
		help="Create a symlink to a project",
		aliases=["ln"])
	p.set_defaults(func=proj.symlink, parser=p)
	_add_project(p, opt=False, cwd=False)
	p.add_argument("filename", 
		help="symlink filename",
		metavar="FILENAME",
		nargs="?")
	return p

def register_list(subparsers):
	p = subparsers.add_parser("list", 
		help="List projects",
		aliases=["ls"])
	p.set_defaults(func=lambda args: print(args), parser=p)
	_add_project(p, opt=True, cwd=False)
	_add_details(p)
	_add_site_opt(p)
	_add_scope_filter(p)
	_add_group_filter(p)
	_add_json(p)
	return p

def register_find(subparsers):
	p = subparsers.add_parser("find", 
		help="Search project metadata",
		aliases=["grep"])
	p.add_argument("query",
		help="search pattern (regex)",
		metavar=SEARCH_HINT)
	_add_details(p)
	_add_site_opt(p)
	_add_scope_filter(p)
	_add_group_filter(p)
	p.add_argument("-w", "--within",
		help="metadata fields to search",
		action="append")
	p.add_argument("-i", "--ignore-case",
		help="ignore case",
		action="store_true")
	_add_json(p)
	return p

def register_fetch(subparsers):
	p = subparsers.add_parser("fetch", 
		help="Get manifest of projects from another site")
	p.add_argument("site", 
		help="site specification",
		metavar=SITE_HINT,
		nargs="?")
	return p

def register_pull(subparsers):
	p = subparsers.add_parser("pull", 
		help="Download a project from another site")
	p.add_argument("site", 
		help="work site specification",
		metavar=SITE_HINT)
	_add_project(p, opt=True, cwd=True)
	_add_force(p)
	_add_dry_run(p)
	_add_ask(p)

def register_push(subparsers):
	p = subparsers.add_parser("push", 
		help="Upload a project to another site")
	p.add_argument("site", 
		help="work site specification",
		metavar=SITE_HINT)
	_add_project(p, opt=True, cwd=True)
	_add_force(p)
	_add_dry_run(p)
	_add_ask(p)
	return p

def register_remove(subparsers):
	p = subparsers.add_parser("remove",
		help="Delete a project",
		aliases=["rm"])
	_add_project(p, opt=False, cwd=False)
	_add_ask(p)
	return p

def register_status(subparsers):
	p = subparsers.add_parser("status", 
		help="Get status of tracked projects")
	return p

def register_site(subparsers):
	p = subparsers.add_parser("site", 
		help="Configure work sites")
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
	p.add_argument("-v", "--verbose", 
		help="verbose output",
		action="store_true")
	p.add_argument("--user", 
		help="site user",
		nargs="?",
		default=False)
	p.add_argument("--host", 
		help="site NODE(s) as <alias>:<host>",
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
	_add_json(p)
	return p

def register_run(subparsers):
	p = subparsers.add_parser("run", 
		help="Run a shell command at another site")
	return p
