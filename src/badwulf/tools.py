
# Tools and utility functions

import os
import re
import platform
import socket
import random
import shutil
from importlib.metadata import version

def badwulf_version():
	"""
	Get badwulf package version
	"""
	return version("badwulf")

def badwulf_attribution():
	"""
	Get badwulf package attribution
	"""
	return "powered by badwulf v" + badwulf_version()

def is_known_host(nodes: list[str]) -> bool:
	"""
	Check if the program is running on a known host
	:param nodes: A list of hostnames
	:returns: True if running on a known host, False otherwise
	"""
	host = platform.node().replace(".local", "")
	nodes = [nodename.casefold() for nodename in nodes]
	return host.casefold() in nodes

def to_bytes(x: int, units: str = "bytes") -> int:
	"""
	Convert a size to bytes
	:param x: A positive number
	:param units: The units for x (KB, MB, GB, etc.)
	:raises ValueError: If units is an invalid string
	:returns: The number of bytes
	"""
	if units in ("bytes", "B"):
		pass
	elif units == "KB":
		x *= 1000
	elif units == "MB":
		x *= 1000 ** 2
	elif units == "GB":
		x *= 1000 ** 3
	elif units == "TB":
		x *= 1000 ** 4
	elif units == "PB":
		x *= 1000 ** 5
	else:
		raise ValueError(f"invalid units: {units}")
	return x

def format_bytes(x: int, units: str = "auto") -> str:
	"""
	Format bytes
	:param x: The number of bytes
	:param units: The units (B, KB, MB, etc.)
	:raises ValueError: If units is an invalid string
	:returns: A string
	"""
	if units == "auto":
		if x >= 1000 ** 5:
			units = "PB"
		elif x >= 1000 ** 4:
			units = "TB"
		elif x >= 1000 ** 3:
			units = "GB"
		elif x >= 1000 ** 2:
			units = "MB"
		elif x >= 1000:
			units = "KB"
		else:
			units = "bytes"
	if units in ("bytes", "B"):
		if x == 1 and units == "bytes":
			units = "byte"
		x = int(x)
	else:
		if units == "KB":
			x /= 1000
		elif units == "MB":
			x /= 1000 ** 2
		elif units == "GB":
			x /= 1000 ** 3
		elif units == "TB":
			x /= 1000 ** 4
		elif units == "PB":
			x /= 1000 ** 5
		else:
			raise ValueError(f"invalid units: {units}")
		x = float(round(x, ndigits=2))
	return f"{x} {units}"

def confirm(msg: str, suffix: str = " (yes/no): ") -> bool:
	"""
	Ask a user to confirm yes or no
	:param msg: The message to print
	:param suffix: The message to print
	:returns: True if yes, False if no
	"""
	while True:
		confirm = input(msg + suffix).casefold()
		if confirm in ("y", "yes"):
			return True
		elif confirm in ("n", "no"):
			return False
		else:
			print("Invalid input. Please enter yes/no.")

def quote(s: str, q: str = '"') -> str:
	"""
	Wrap a string in quotes
	:param s: The string to quote
	:returns: A quoted string
	"""
	if s[0] != q and s[-1] != q:
		return q + s + q
	else:
		return s

def fix_path(
	path: str, 
	must_exist: bool = True, 
	escape_spaces: bool = False) -> str:
	"""
	Normalize and expand paths
	:param path: The path to normalize
	:param must_exist: Must the path exist?
	:raises FileNotFoundError: If the file doesn't exist
	:returns: The normalized path
	"""
	if "~" in path:
		path = os.path.expanduser(path)
	path = os.path.realpath(path)
	if must_exist and not os.path.exists(path):
		raise FileNotFoundError(f"path does not exist: '{path}'")
	if escape_spaces:
		path = path.replace(" ", r"\ ")
	return path

def ls(path: str = ".", all_names: bool = False) -> list[str]:
	"""
	List files in a directory
	:param path: The directory
	:param all_names: Should hidden files be included?
	:raises NotADirectoryError: If path isn't a directory
	:returns: A list of file names
	"""
	path = fix_path(path)
	if not os.path.isdir(path):
		raise NotADirectoryError(f"path must be a directory: {path}")
	if all_names:
		return [f for f in os.listdir(path)]
	else:
		return [f for f in os.listdir(path) if not f.startswith(".")]

def file_create(path: str) -> None:
	"""
	Create a file
	:param path: The file to create
	"""
	path = fix_path(path, must_exist=False)
	with open(path, "a"):
		os.utime(path, None)

def file_remove(path: str) -> None:
	"""
	Delete a file
	:param path: The file to delete
	"""
	path = fix_path(path, must_exist=False)
	if os.path.exists(path):
		os.remove(path)

def dir_create(path: str, force: bool = False) -> None:
	"""
	Create a directory
	:param path: The directory to create
	:param force: Create intermediate directories if they don't exist?
	"""
	path = fix_path(path, must_exist=False)
	if not os.path.exists(path):
		if force:
			os.makedirs(path)
		else:
			os.mkdir(path)

def dir_remove(path: str, force: bool = False) -> None:
	"""
	Delete a directory
	:param path: The directory to delete
	:param force: Delete all directory contents if not empty?
	"""
	path = fix_path(path, must_exist=False)
	if os.path.exists(path):
		if force:
			shutil.rmtree(path)
		else:
			os.rmdir(path)

def tree_find(
	path: str, 
	pattern: str,
	ignore_case: bool = False,
	prune_on_match: bool = False) -> list[str]:
	"""
	Find files in a directory matching a pattern
	:param path: The directory
	:param pattern: The pattern
	:param ignore_case: Should case be ignored?
	:param prune_on_match: Prevent descending past matches?
	:returns: A list of matching file paths
	"""
	matches = []
	for dirpath, dirnames, filenames in os.walk(path):
		for name in filenames:
			if grep1(pattern, name, ignore_case) is not None:
				matches.append(os.path.join(dirpath, name))
				if prune_on_match:
					dirnames.clear()
	return matches

def tree_stat(
	path: str, 
	time_exclude: set[str] = None,
	size_exclude: set[str] = None) -> dict[str, int | float]:
	"""
	Recursively summarize max atime, max mtime, and total size of a tree
	:param path: Path of directory to summarize
	:param time_exclude: A set of file names to exclude from time stats
	:param size_exclude: A set of file names to exclude from size stats
	:returns: A dict containing atime, mtime, and size
	"""
	if not os.path.isdir(path):
		raise NotADirectoryError(f"path must be a directory: {path}")
	atime = 0
	mtime = os.path.getmtime(path)
	size = 0
	it = os.scandir(path)
	with os.scandir(path) as it:
		for file in it:
			if file.is_dir(follow_symlinks=False):
				st = tree_stat(file.path, 
					time_exclude=time_exclude,
					size_exclude=size_exclude)
			else:
				st = file.stat()
				st = {
					"atime": st.st_atime, 
					"mtime": st.st_mtime, 
					"size": st.st_size}
			if time_exclude is None or file.name not in time_exclude:
				atime = max(atime, st["atime"])
				mtime = max(mtime, st["mtime"])
			if size_exclude is None or file.name not in size_exclude:
				size += st["size"]
	return {"atime": atime, "mtime": mtime, "size": size}

def tree_size(path: str) -> int:
	"""
	Get size of a directory's contents
	:param path: The directory
	:returns: The size of the directory in bytes
	"""
	return tree_stat(path)["size"]

def checkport(port: int) -> int:
	"""
	Check if a port is open (i.e., if it is in use)
	:param port: The port to check
	:returns: 0 if open, an error code otherwise
	"""
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	result = sock.connect_ex(("localhost", port))
	sock.close()
	return result

def findport(attempts: int = 10) -> int:
	"""
	Find an available port (for SSH forwarding)
	:param attempts: How many random ports to attempt
	:raises IOError: If a port can't be found
	:returns: The port number
	"""
	for i in range(attempts):
		port = random.randint(1024, 65535)
		if checkport(port) != 0:
			return port
	raise IOError("couldn't find an available port")

def grep1(
	pattern: str, 
	x: str, 
	ignore_case: bool = False, 
	context_width: int | None = None) -> re.Match | None:
	"""
	Search for a pattern in a string
	:param pattern: The pattern to find
	:param x: A string
	:param ignore_case: Should case be ignored?
	:param context_width: Width of a context window to return
	:param fixed_string: Interpret pattern as fixed string
	:returns: A Match or None
	"""
	if x is None:
		return None
	if ignore_case:
		match = re.search(pattern, x, flags=re.IGNORECASE)
	else:
		match = re.search(pattern, x)
	if match is None or context_width is None:
		return match
	else:
		start = match.start()
		stop = match.end()
		margin = ((context_width - (stop - start)) // 2)
		if context_width > len(x):
			return x
		if context_width < stop - start or margin < 4:
			return x[start:stop]
		pre, post = "", ""
		if start > margin:
			start = max(0, start - margin)
			pre = "..."
		if len(x) - stop > margin:
			stop = min(len(x), stop + margin)
			post = "..."
		return pre + x[start:stop] + post

def grep(
	pattern: str, 
	x: str | list | dict | None, 
	ignore_case: bool = False,
	context_width: int | None = None) -> str | list | dict | None:
	"""
	Recursively search for a pattern in anything
	:param pattern: The pattern to find
	:param x: A string or iterable
	:param ignore_case: Should case be ignored?
	:param context_width: Width of a context window to return
	:raises TypeError: If x is an unsupported type
	:returns: Matches in the same shape as x
	"""
	match x:
		case str():
			return grep1(pattern, x, ignore_case, context_width)
		case list():
			return [
				grep(pattern, xi, ignore_case, context_width) 
				for xi in x]
		case dict():
			return {
				k: grep(pattern, v, ignore_case, context_width) 
				for k, v in x.items()}
		case None:
			return None
		case _:
			raise TypeError("unsupported type")

def prune(x: list | dict, recursive: bool = True) -> list | dict:
	"""
	Recursively remove None and empty lists and dicts
	:param x: An iterable to prune
	:param recursive: Should collections in x also be pruned?
	:raises TypeError: If x is an unsupported type
	:returns: A pruned result in the same shape as x
	"""
	match x:
		case list():
			pruned = []
			for xi in x:
				if isinstance(xi, (list, dict)) and recursive:
					xi = prune(xi)
					if len(xi) == 0:
						continue
				if xi is not None:
					pruned.append(xi)
		case dict():
			pruned = {}
			for k, v, in x.items():
				if isinstance(v, (list, dict)) and recursive:
					v = prune(v)
					if len(v) == 0:
						continue
				if v is not None:
					pruned[k] = v
		case _:
			raise TypeError("unsupported type")
	return pruned

def rekey_kebab_to_snake(d: dict) -> dict:
	"""
	Rekeys a dict from kebab-case to snake_case
	:param d: The dict to rekey
	:returns: A rekeyed dict
	"""
	return {k.replace("-", "_"): v for k, v in d.items()}

def rekey_snake_to_kebab(d: dict) -> dict:
	"""
	Rekeys a dict from snake-case to kebab-case
	:param d: The dict to rekey
	:returns: A rekeyed dict
	"""
	return {k.replace("_", "-"): v for k, v in d.items()}

def maybe_template(s: str) -> bool:
	"""
	Checks if a string is likely an unformatted f-string template
	:param s: String to check
	:returns: True if likely an f-string template, False otherwise
	"""
	pattern = re.compile(r"\{[^{}]*\}")
	s = s.replace("{{", "").replace("}}", "")
	return pattern.search(s) is not None
