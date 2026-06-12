import os
import sys
import json

from ..sync import profile
from ..sync import syncer
from ..util import prog_error
from ..util import tokenize
from ..util import mkpath
from ..util import detect
from ..util import prune

def tokenize_to_dict(*items):
	items = [tokenize(s) for s in items if s is not None]
	return {k: v for k, v in items}

def detect_sites():
	if "BADWULF_SITES" in os.environ:
		path = mkpath(os.getenv("BADWULF_SITES"))
	else:
		try:
			path = detect(r"\.?badwulf-sites\.json$", 
				".", "~", mkpath("~", ".badwulf"))
		except FileNotFoundError:
			prefix = mkpath("~", ".badwulf")
			path = mkpath(prefix, "badwulf-sites.json")
			site = profile(paths={"default": prefix})
			cfg = syncer({"self": site})
			with open(path, "w") as f:
				json.dump(cfg.to_dict(), f, indent="\t")
	return path

def load_sites():
	return syncer.from_path(detect_sites())

def list_sites(path, args):
	cfg = syncer.from_path(path)
	if args.json:
		print(json.dumps(cfg.to_dict(), indent=2))
	else:
		print(f"{path}:")
		for name in cfg.sites.keys():
			if name == "self":
				print(f"* {name}")
			else:
				print(f"  {name}")

def add_site(path, args):
	cfg = syncer.from_path(path)
	if args.name in cfg.sites:
		prog_error(f"site '{args.name}' already exists", args)
	else:
		cfg.sites[args.name] = profile()
	with open(path, "w") as f:
		json.dump(cfg.to_dict(), f, indent="\t")
	if not all_unset(args):
		set_site(path, args)

def get_site(path, args):
	cfg = syncer.from_path(path)
	site = cfg.sites.get(args.name)
	if site is None:
		prog_error(f"no site named '{args.name}'", args)
	if all_unset(args):
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
		render_site(d)

def set_site(path, args):
	cfg = syncer.from_path(path)
	site = cfg.sites.get(args.name)
	if site is None:
		prog_error(f"no site named '{args.name}'", args)
	if all_unset(args):
		args.parser.error("expected one or more site variables")
	else:
		if args.user is not False:
			if args.user is None:
				site.user = ""
			else:
				site.user = args.user
		hosts = prune(args.host)
		if len(hosts) > 0:
			for k, v in tokenize_to_dict(*hosts).items():
				if v is None:
					if k in site.hosts:
						del site.hosts[k]
				else:
					if v == "":
						prog_error("empty string invalid for hosts", args)
					site.hosts[k] = v
		paths = prune(args.path)
		if len(paths) > 0:
			for k, v in tokenize_to_dict(*paths).items():
				if v is None:
					if k in site.paths:
						del site.paths[k]
				else:
					site.paths[k] = v
		if args.proxy_user is not False:
			if args.proxy_user is None:
				site.proxy["user"] = ""
			else:
				site.proxy["user"] = args.proxy_user
		if args.proxy_host is not False:
			if args.proxy_host is None:
				del site.proxy["host"]
			else:
				if args.proxy_host == "":
					prog_error("empty string invalid for hosts", args)
				site.proxy["host"] = args.proxy_host
	with open(path, "w") as f:
		json.dump(cfg.to_dict(), f, indent="\t")

def remove_site(path, args):
	cfg = syncer.from_path(path)
	if args.name not in cfg.sites:
		prog_error(f"no site named '{args.name}'", args)
	else:
		del cfg.sites[args.name]
	with open(path, "w") as f:
		json.dump(cfg.to_dict(), f, indent="\t")

def render_site(d):
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

def all_unset(args):
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
