import os
import json

from ..sync import profile
from ..sync import syncer
from ..util import prog_error
from ..util import tokenize
from ..util import mkpath
from ..util import mktree
from ..util import detect
from ..util import prune

DEFAULT_SITE = "local"
DEFAULT_HOST = "default"
DEFAULT_PREFIX = "default"

def detect_sites():
	if "BADWULF_SITES" in os.environ:
		path = mkpath(os.getenv("BADWULF_SITES"))
	else:
		try:
			path = detect(r"^\.?badwulf-sites\.json$", 
				".", "~", mkpath("~", ".badwulf"))
		except FileNotFoundError:
			prefix = mkpath("~", ".badwulf")
			if not os.path.isdir(prefix):
				mktree(prefix)
			path = mkpath(prefix, "badwulf-sites.json")
			site = profile(paths={DEFAULT_PREFIX: prefix})
			sts = syncer({DEFAULT_SITE: site})
			with open(path, "w") as f:
				json.dump(sts.to_dict(), f, indent="\t")
	return path

def load_sites():
	return syncer.from_path(detect_sites())

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

def tokenize_to_dict(*items):
	items = [tokenize(s) for s in items if s is not None]
	return {k: v for k, v in items}

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

def show(args):
	path = detect_sites()
	sts = syncer.from_path(path)
	if args.json:
		print(json.dumps(sts.to_dict(), indent=2))
	else:
		if args.verbose:
			print(f"{path}:")
			d = sts.to_dict()
			print()
			for name in sts.keys():
				print(f"{name}:")
				print_site(d[name])
				print()
		else:
			for name in sts.keys():
				if name == DEFAULT_SITE:
					print(f"{name} *")
				else:
					print(f"{name}")

def add(args):
	path = detect_sites()
	sts = syncer.from_path(path)
	if args.name in sts:
		prog_error(f"site '{args.name}' already exists", args)
	else:
		sts[args.name] = profile()
	with open(path, "w") as f:
		json.dump(sts.to_dict(), f, indent="\t")
	if not all_missing(args):
		set_vars(args)

def get_vars(args):
	sts = load_sites()
	site = sts.get(args.name)
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
	path = detect_sites()
	sts = syncer.from_path(path)
	site = sts.get(args.name)
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
	with open(path, "w") as f:
		json.dump(sts.to_dict(), f, indent="\t")

def unset_vars(args):
	path = detect_sites()
	sts = syncer.from_path(path)
	site = sts.get(args.name)
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
	with open(path, "w") as f:
		json.dump(sts.to_dict(), f, indent="\t")

def remove(args):
	path = detect_sites()
	sts = syncer.from_path(path)
	if args.name not in sts:
		prog_error(f"no site named '{args.name}'", args)
	else:
		del sts[args.name]
	with open(path, "w") as f:
		json.dump(sts.to_dict(), f, indent="\t")

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
