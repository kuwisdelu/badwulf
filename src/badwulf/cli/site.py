import os
import json

from ..core import profile
from ..core import dbsyncer
from ..util import prog_error
from ..util import tokenize
from ..util import mkpath
from ..util import mktree
from ..util import detect
from ..util import prune

def tokenize_to_dict(*items):
	items = [tokenize(s) for s in items if s is not None]
	return {k: v for k, v in items}

def all_missing(args):
	if args.user is not False:
		return False
	if len(args.host) > 0:
		return False
	if len(args.path) > 0:
		return False
	if args.proxy_user is not False:
		return False
	if args.proxy_host is not False:
		return False
	return True

def main(args):
	match args.subcommand:
		case None:
			show(args)
		case "add":
			add(args)
		case "get":
			get_vars(args)
		case "set":
			set_vars(args)
		case "unset":
			unset_vars(args)
		case "remove":
			remove(args)

def add(args):
	dbs = dbsyncer.from_default_locations()
	if args.name in dbs.sites:
		prog_error(f"site '{args.name}' already exists", args)
	dbs.sites[args.name] = profile()
	dbs.save_sites()
	if not all_missing(args):
		set_vars(args)

def get_vars(args):
	dbs = dbsyncer.from_default_locations()
	site = dbs.sites.get(args.name)
	if site is None:
		prog_error(f"no site named '{args.name}'", args)
	if all_missing(args):
		d = {
			"user": site.user,
			"hosts": site.hosts,
			"paths": site.paths,
			"proxy": site.proxy}
	else:
		d = {
			"user": None, 
			"hosts": {},
			"paths": {},
			"proxy": {}}
		if args.user is not False:
			test, user = args.user, site.user
			if test is None or test.casefold() == user.casefold():
				d["user"] = user
		if len(args.host) > 0:
			if all(args.host):
				for k, v in tokenize_to_dict(*args.host).items():
					if k in site.hosts:
						host = site.hosts[k]
						if v is None or v.casefold() == host.casefold():
							d["hosts"][k] = host
			else:
				d["hosts"] = site.hosts
		if len(args.path) > 0:
			if all(args.path):
				for k, v in tokenize_to_dict(*args.path).items():
					if k in site.paths:
						path = site.paths[k]
						if v is None or v.casefold() == path.casefold():
							d["paths"][k] = path
			else:
				d["paths"] = site.paths
		if args.proxy_user is not False and "user" in site.proxy:
			test, user = args.proxy_user, site.proxy["user"]
			if test is None or test.casefold() == user.casefold():
				d["proxy"]["user"] = user
		if args.proxy_host is not False and "host" in site.proxy:
			test, host = args.proxy_host, site.proxy["host"]
			if test is None or test.casefold() == host.casefold():
				d["proxy"]["host"] = host
	d = prune(d)
	if args.json:
		print(json.dumps(d, indent=2))		
	else:
		print_site(d)

def set_vars(args):
	dbs = dbsyncer.from_default_locations()
	site = dbs.sites.get(args.name)
	if site is None:
		prog_error(f"no site named '{args.name}'", args)
	if all_missing(args):
		args.parser.error("expected one or more site variables")
	else:
		if args.user is not False:
			if args.user is None:
				args.parser.error("expected argument to set --user")
			else:
				site.user = args.user
		if len(args.host) > 0:
			if not all(args.host):
				args.parser.error("expected argument to set --host")
			else:
				args.host = prune(args.host)
			for k, v in tokenize_to_dict(*args.host).items():
				if v is None:
					args.parser.error(f"expected value to set --host {k}:")
				elif v == "":
					prog_error("empty string invalid for hosts", args)
				else:
					site.hosts[k] = v
		if len(args.path) > 0:
			if not all(args.path):
				args.parser.error("expected argument to set --path")
			else:
				args.path = prune(args.path)
			for k, v in tokenize_to_dict(*args.path).items():
				if v is None:
					args.parser.error(f"expected value to set --path {k}:")
				else:
					site.paths[k] = v
		if args.proxy_user is not False:
			if args.proxy_user is None:
				args.parser.error("expected argument to set --proxy-user")
			else:
				site.proxy["user"] = args.proxy_user
		if args.proxy_host is not False:
			if args.proxy_host is None:
				args.parser.error("expected argument to set --proxy-host")
			elif args.proxy_host == "":
				prog_error("empty string invalid for hosts", args)
			else:
				site.proxy["host"] = args.proxy_host
	dbs.save_sites()

def unset_vars(args):
	dbs = dbsyncer.from_default_locations()
	site = dbs.sites.get(args.name)
	if site is None:
		prog_error(f"no site named '{args.name}'", args)
	if all_missing(args):
		args.parser.error("expected one or more site variables")
	else:
		if args.user is not False:
			if args.user is None:
				site.user = ""
			else:
				args.parser.error("unexpected argument to unset --user")
		if len(args.host) > 0:
			if not any(args.host):
				args.parser.error("expected argument to unset --host")
			else:
				args.host = prune(args.host)
			for k, v in tokenize_to_dict(*args.host).items():
				if v is None:
					if k in site.hosts:
						del site.hosts[k]
					else:
						prog_error(f"no host named: {k}")
				else:
					args.parser.error(f"unexpected value to unset --host {k}")
		if len(args.path) > 0:
			if not any(args.path):
				args.parser.error("expected argument to unset --path")
			else:
				args.path = prune(args.path)
			for k, v in tokenize_to_dict(*args.path).items():
				if v is None:
					if k in site.paths:
						del site.paths[k]
					else:
						prog_error(f"no path named: {k}")
				else:
					args.parser.error(f"unexpected value to unset --path {k}")
		if args.proxy_user is not False:
			if args.proxy_user is None:
				del site.proxy_user["user"]
			else:
				args.parser.error("unexpected argument to unset --proxy-user")
		if args.proxy_host is not False:
			if args.proxy_host is None:
				del site.proxy_user["host"]
			else:
				args.parser.error("unexpected argument to unset --proxy-host")
	dbs.save_sites()

def remove(args):
	dbs = dbsyncer.from_default_locations()
	if args.name not in dbs.sites:
		prog_error(f"no site named '{args.name}'", args)
	else:
		del dbs.sites[args.name]
	dbs.save_sites()

def show(args):
	dbs = dbsyncer.from_default_locations()
	if args.json:
		print(json.dumps(dbs.sites.to_dict(), indent=2))
	else:
		if args.verbose:
			print(f"{dbs.sites_path}:")
			d = dbs.sites.to_dict()
			print()
			for name in dbs.sites.keys():
				print(f"{name}:")
				print_site(d[name])
				print()
		else:
			for name in dbs.sites.keys():
				if name == dbs.local_name:
					print(f"{name} *")
				else:
					print(f"{name}")

def run(args):
	prog_error("NOT IMPLEMENTED YET", args)

def print_site(d):
	if "user" in d:
		print(f"user={d["user"]}")
	if "hosts" in d:
		for k, v in d["hosts"].items():
			print(f"host={k}:{v}")
	if "paths" in d:
		for k, v in d["paths"].items():
			print(f"path={k}:{v}")
	if "proxy" in d and "user" in d["proxy"]:
		print(f"proxy-user={d["proxy"]["user"]}")
	if "proxy" in d and "host" in d["proxy"]:
		print(f"proxy-host={d["proxy"]["host"]}")
