
# Tools and utility functions

import os
import re
import sys
import socket
import random
import shutil
import argparse

def prog_text(
	text: str, 
	args: argparse.Namespace, 
	label: str | None = None) -> str:
	"""
	Get text formatted as a message from a program
	:param text: The program message
	:param args: Namespace from argparse (must include "parser")
	:param label: A label (e.g., "error", "warning", etc.)
	"""
	if label is None:
		return f"{args.parser.prog}: {text}"
	else:
		return f"{args.parser.prog}: {label}: {text}"

def prog_error(text: str | Exception, args: argparse.Namespace) -> None:
	"""
	Exit a program with a formatted error message
	:param text: The error message
	:param args: Namespace from argparse (must include "parser")
	:raises SystemExit: With a nonzero exit code
	"""
	if isinstance(text, Exception):
		if isinstance(text, KeyError):
			text = text.args[0]
		else:
			text = str(text)
	sys.exit(prog_text(text, args, label="error"))

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

def tokenize(text: str | None, sep: str = ":") -> tuple[str | None]:
	"""
	Tokenize into two strings based on the first separator
	"""
	if text is None:
		return (None, None)
	s1, sep, s2 = text.partition(sep)
	if sep == "":
		return (text, None)
	else:
		return (s1, s2)

def rtokenize(text: str | None, sep: str = ":") -> tuple[str | None]:
	"""
	Tokenize into two strings based on the last separator
	"""
	if text is None:
		return (None, None)
	s1, sep, s2 = text.rpartition(sep)
	if sep == "":
		return (None, text)
	else:
		return (s1, s2)

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

def touch(path: str, times: tuple(float) | None = None) -> None:
	"""
	Modify a file's atime and mtime and create it if it doesn't exist
	:param path: The file to create or modify
	:param path: The times as a tuple (atime, mtime)
	"""
	path = mkpath(path, must_exist=False)
	with open(path, "a"):
		os.utime(path, times)

def mkpath(
	*paths: str, 
	must_exist: bool = False,
	escape_spaces: bool = False) -> str:
	"""
	Join and normalize file paths
	:param paths: Path components to join and normalize
	:param must_exist: Must the path exist?
	:param escape_spaces: Escape spaces with backslashes?
	:raises FileNotFoundError: If must_exist and the file doesn't exist
	:returns: The normalized path
	"""
	path = os.path.join(*paths)
	if "$" in path:
		path = os.path.expandvars(path)
	if "~" in path:
		path = os.path.expanduser(path)
	path = os.path.realpath(path)
	if must_exist and not os.path.exists(path):
		raise FileNotFoundError(f"path does not exist: '{path}'")
	if escape_spaces:
		path = path.replace(" ", r"\ ")
	return path

def mktree(path: str, force: bool = False) -> None:
	"""
	Create a directory tree
	:param path: The directory tree to create
	:param force: Create intermediate directories if they don't exist?
	"""
	path = mkpath(path, must_exist=False)
	if not os.path.exists(path):
		if force:
			os.makedirs(path)
		else:
			os.mkdir(path)

def rmtree(path: str, force: bool = False) -> None:
	"""
	Delete a directory tree
	:param path: The directory tree to delete
	:param force: Delete all directory contents if not empty?
	"""
	path = mkpath(path, must_exist=False)
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
	exclude: str | None = None,
	ignore_case: bool = False) -> dict[str, int | float]:
	"""
	Aggregate size and mtime of a directory tree
	:param path: Path of directory to summarize
	:param exclude: A pattern of path names to exclude
	:returns: A dict containing aggregate 'size' and 'mtime'
	"""
	if not os.path.isdir(path):
		raise NotADirectoryError(f"path must be a directory: {path}")
	mtime = os.path.getmtime(path)
	size = 0
	err = []
	with os.scandir(path) as it:
		for file in it:
			if exclude is not None:
				if grep1(exclude, file.name, ignore_case) is not None:
					continue
			if file.is_symlink():
				try:
					st = file.stat()
				except OSError as e:
					err.append(str(e))
				continue
			if file.is_dir():
				st = tree_stat(
					path=file.path, 
					exclude=exclude, 
					ignore_case=ignore_case)
			else:
				st = file.stat()
				st = {"size": st.st_size, "mtime": st.st_mtime}
				mtime = max(mtime, st["mtime"])
				size += st["size"]
	if len(err) > 0:
		return {"size": size, "mtime": mtime, "err": err}
	else:
		return {"size": size, "mtime": mtime}

def detect(
	pattern: str,
	*paths: str,
	ignore_case: bool = False) -> str:
	"""
	Detect a file pattern in a multiple possible directories
	:param pattern: The pattern
	:param paths: The directories (in priority order)
	:param ignore_case: Should case be ignored?
	:raises FileNotFoundError: If the file pattern can't be found
	:returns: The path of the first detected file
	"""
	for path in (mkpath(p) for p in paths):
		if os.path.isdir(path):
			filenames = os.listdir(path)
			for name in filenames:
				if grep1(pattern, name, ignore_case) is not None:
					return mkpath(path, name)
	raise FileNotFoundError(f"no match for {pattern}")

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
	raise IOError("no available port")

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
		case _:
			return None

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
			raise TypeError("expected a list or dict")
	return pruned
