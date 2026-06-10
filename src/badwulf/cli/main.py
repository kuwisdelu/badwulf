import argparse
from importlib import metadata

def main():
	args = build_parser().parse_args()
	args.func(args)

def build_parser():
	p = argparse.ArgumentParser(prog="wulf")
	p.set_defaults(func=lambda args: p.print_help())
	p.add_argument("-v", "--version", 
		help="show version",
		action="version",
		version=f"badwulf {metadata.version("badwulf")}")
	sub = p.add_subparsers(metavar="COMMAND")
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
	cmd = subparsers.add_parser("init", 
		help="Create an empty project")
	cmd.set_defaults(func=cmd_init)
	return cmd

def cmd_init(args):
	print("hello, world!")

def register_clone(subparsers):
	cmd = subparsers.add_parser("clone", 
		help="Create a symlink to a project",
		aliases=["ln"])
	return cmd

def register_list(subparsers):
	cmd = subparsers.add_parser("list", 
		help="List projects",
		aliases=["ls"])
	cmd.add_argument("-l", "--details", 
		help="show extended details",
		action="store_true")
	cmd.add_argument("-s", "--scope", 
		help="filter by scope",
		action="store")
	cmd.add_argument("-g", "--group", 
		help="filter by group",
		action="store")
	return cmd

def register_find(subparsers):
	cmd = subparsers.add_parser("find", 
		help="Search project metadata",
		aliases=["grep"])
	cmd.add_argument("-s", "--scope", 
		help="filter by scope",
		action="store")
	cmd.add_argument("-g", "--group", 
		help="filter by group",
		action="store")
	return cmd

def register_fetch(subparsers):
	cmd = subparsers.add_parser("fetch", 
		help="Get manifest of projects from another site")
	return cmd

def register_pull(subparsers):
	cmd = subparsers.add_parser("pull", 
		help="Download a project from another site")
	cmd.add_argument("-f", "--force", 
		help="force download even if the other is older?",
		action="store_true")
	cmd.add_argument("--dry-run", 
		help="show what would happen without doing it?",
		action="store_true")
	cmd.add_argument("--ask", 
		help="ask to confirm before pushing?",
		action="store_true")

def register_push(subparsers):
	cmd = subparsers.add_parser("push", 
		help="Upload a project to another site")
	cmd.add_argument("-f", "--force", 
		help="force upload even if the other is newer?",
		action="store_true")
	cmd.add_argument("--dry-run", 
		help="show what would happen without doing it?",
		action="store_true")
	cmd.add_argument("--ask", 
		help="ask to confirm before pushing?",
		action="store_true")
	return cmd

def register_remove(subparsers):
	cmd = subparsers.add_parser("remove",
		help="Delete a project",
		aliases=["rm"])
	cmd.add_argument("-f", "--force", 
		help="force upload even if the other is newer?",
		action="store_true")
	cmd.add_argument("--dry-run", 
		help="show what would happen without doing it?",
		action="store_true")
	cmd.add_argument("--ask", 
		help="ask to confirm before pushing?",
		action="store_true")
	return cmd

def register_status(subparsers):
	cmd = subparsers.add_parser("status", 
		help="Get status of tracked projects")
	return cmd

def register_site(subparsers):
	cmd = subparsers.add_parser("site",
		help="Get or set work site configuration")
	return cmd

def register_run(subparsers):
	cmd = subparsers.add_parser("run", 
		help="Run a shell command at another site")
	return cmd
