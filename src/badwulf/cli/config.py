import os
import sys
import json

from ..sync import syncer
from ..util import mkpath
from ..util import detect
from ..util import prune

def as_dict(*items):
	def separate(s, sep):
		if sep in s:
			return s.partition(sep)
		else:
			return (s, sep, None)
	items = [separate(s, ":") for s in items if s is not None]
	return {k: v for k, sep, v in items}

def get_syncer():
	if "BADWULF_SITES" in os.environ:
		path = mkpath(os.getenv("BADWULF_SITES"))
	else:
		try:
			path = detect(r"\.?badwulf-sites\.json$", 
				".", "~", mkpath("~", ".badwulf"))
		except FileNotFoundError:
			prefix = mkpath("~", ".badwulf")
			path = mkpath(prefix, "badwulf-sites.json")
			site = {"user": "", "paths": {"default": prefix}}
			with open(path) as f:
				json.dump({"self": site}, f, indent="\t")
	return syncer.from_path(path)

def get_site(cfg, args):
	site = cfg.sites.get(args.name)
	if site is None:
		sys.exit(f"no site named '{args.name}'")
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
		if args.user is None or args.user == site.user:
			d["user"] = site.user
		if len(args.host) > 0:
			if all(args.host):
				for k, v in as_dict(*args.host).items():
					if k in site.hosts:
						host = site.hosts[k]
						if v is None:
							d["hosts"][k] = host
						elif v.casefold() == host.casefold():
							d["hosts"][k] = host
			else:
				d["hosts"] = site.hosts
		if len(args.path) > 0:
			if all(args.path):
				for k, v in as_dict(*args.path).items():
					if k in site.paths:
						path = site.paths[k]
						if v is None:
							d["paths"][k] = path
						elif v.casefold() == path.casefold():
							d["paths"][k] = path
			else:
				d["paths"] = site.paths
		proxy_user = site.proxy.get("user")
		if args.proxy_user is not False and proxy_user is not None:
			if args.proxy_user is None:
				d["proxy"]["user"] = proxy_user
			elif args.proxy_user.casefold() == proxy_user.casefold():
				d["proxy"]["user"] = proxy_user
		proxy_host = site.proxy.get("host")
		if args.proxy_host is not False and proxy_host is not None:
			if args.proxy_host is None:
				d["proxy"]["user"] = proxy_host
			elif args.proxy_host.casefold() == proxy_host.casefold():
				d["proxy"]["user"] = proxy_host
	d = prune(d)
	if args.json:
		print(json.dumps(d, indent=2))		
	else:
		render_site(d)

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
