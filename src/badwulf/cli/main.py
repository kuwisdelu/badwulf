import os
import sys
import json
import argparse
from importlib import metadata

from ..sync import syncer
from .config import detect_sites
from .config import load_sites
from .config import list_sites
from .config import add_site
from .config import get_site
from .config import set_site
from .config import remove_site

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
	# create and explore
	register_init(sub)
	register_clone(sub)
	register_list(sub)
	register_find(sub)
	# work and sync projects
	register_fetch(sub)
	register_pull(sub)
	register_push(sub)
	register_remove(sub)
	# configure and connect
	register_status(sub)
	register_site(sub)
	register_run(sub)
	return p

def register_init(subparsers):
	p = subparsers.add_parser("init", 
		help="Create an empty project")
	p.set_defaults(func=cmd_init)
	return p

def cmd_init(args):
	print("hello, world!")

def register_clone(subparsers):
	p = subparsers.add_parser("clone", 
		help="Create a symlink to a project",
		aliases=["ln"])
	return p

def register_list(subparsers):
	p = subparsers.add_parser("list", 
		help="List projects",
		aliases=["ls"])
	p.add_argument("-l", "--details", 
		help="show details",
		action="store_true")
	p.add_argument("-s", "--scope", 
		help="filter by scope",
		action="store")
	p.add_argument("-g", "--group", 
		help="filter by group",
		action="store")
	p.add_argument("--json", 
		help="json output",
		action="store_true")
	return p

def register_find(subparsers):
	p = subparsers.add_parser("find", 
		help="Search project metadata",
		aliases=["grep"])
	p.add_argument("-l", "--details", 
		help="show details",
		action="store_true")
	p.add_argument("-s", "--scope", 
		help="filter by scope",
		action="store")
	p.add_argument("-g", "--group", 
		help="filter by group",
		action="store")
	p.add_argument("--json", 
		help="json output",
		action="store_true")
	return p

def register_fetch(subparsers):
	p = subparsers.add_parser("fetch", 
		help="Get manifest of projects from another site")
	return p

def register_pull(subparsers):
	p = subparsers.add_parser("pull", 
		help="Download a project from another site")
	p.add_argument("-f", "--force", 
		help="force download even if the other is older?",
		action="store_true")
	p.add_argument("--dry-run", 
		help="show what would happen without doing it?",
		action="store_true")
	p.add_argument("--ask", 
		help="ask to confirm before pushing?",
		action="store_true")

def register_push(subparsers):
	p = subparsers.add_parser("push", 
		help="Upload a project to another site")
	p.add_argument("-f", "--force", 
		help="force upload even if the other is newer?",
		action="store_true")
	p.add_argument("--dry-run", 
		help="show what would happen without doing it?",
		action="store_true")
	p.add_argument("--ask", 
		help="ask to confirm before pushing?",
		action="store_true")
	return p

def register_remove(subparsers):
	p = subparsers.add_parser("remove",
		help="Delete a project",
		aliases=["rm"])
	p.add_argument("-f", "--force", 
		help="force upload even if the other is newer?",
		action="store_true")
	p.add_argument("--dry-run", 
		help="show what would happen without doing it?",
		action="store_true")
	p.add_argument("--ask", 
		help="ask to confirm before pushing?",
		action="store_true")
	return p

def register_status(subparsers):
	p = subparsers.add_parser("status", 
		help="Get status of tracked projects")
	return p

def register_site(subparsers):
	p = subparsers.add_parser("site", 
		help="Configure work sites")
	p.set_defaults(func=cmd_site, parser=p)
	p.add_argument("subcommand",
		help="Add, get, set, or remove site configuration",
		choices=["add", "get", "set", "remove"],
		nargs="?")
	p.add_argument("name",
		help="The site name",
		default="self",
		nargs="?")
	p.add_argument("--user", 
		help="site user",
		nargs="?",
		default=False)
	p.add_argument("--host", 
		help="site hosts as <alias>:<host>",
		action="append",
		nargs="?",
		default=[])
	p.add_argument("--path", 
		help="site paths as <alias>:<path>",
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
	p.add_argument("--json", 
		help="json output",
		action="store_true")
	return p

def cmd_site(args):
	path = detect_sites()
	match args.subcommand:
		case None:
			list_sites(path, args)
		case "add":
			add_site(path, args)
		case "set":
			set_site(path, args)
		case "get":
			get_site(path, args)
		case "remove":
			remove_site(path, args)

def register_run(subparsers):
	p = subparsers.add_parser("run", 
		help="Run a shell command at another site")
	return p
