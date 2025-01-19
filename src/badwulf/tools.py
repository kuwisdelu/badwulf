
# Tools and utility functions

import os
import re
import platform
import socket
import random
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
	str1 = "powered by badwulf |"
	str2 = "copyright (c) 2024 Kylie A. Bemis"
	return str1 + " " + str2

def is_known_host(nodes):
	"""
	Check if the program is running on a known host
	:param nodes: A list of hostnames
	:returns: True if running on a known host, False otherwise
	"""
	host = platform.node().replace(".local", "")
	nodes = [nodename.casefold() for nodename in nodes]
	return host.casefold() in nodes

def to_bytes(x, units = "bytes"):
	"""
	Convert a size to bytes
	:param x: A positive number
	:param units: The units for x (KB, MB, GB, etc.)
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

def format_bytes(x, units = "auto"):
	"""
	Format bytes
	:param x: The number of bytes
	:param units: The units (B, KB, MB, etc.)
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
		x = round(x, ndigits=2)
		x = float(x)
	return f"{x} {units}"

def print_bytes(x, units = "auto"):
	"""
	Print bytes
	:param x: The number of bytes
	:param units: The units (B, KB, MB, etc.)
	"""
	print(format_bytes(x, units))

def format_datasets(iterable, names_only = False, header = True):
	"""
	Format datasets
	:param iterable: An iterable of datasets
	:param names_only: Print names only?
	:param header: Print number of datasets?
	:return: A formatted string
	"""
	if names_only:
		sl = [f"['{dataset.name}']" 
			for dataset 
			in iterable]
	else:
		sl = [f"['{dataset.name}']\n{dataset}" 
			for dataset 
			in iterable]
	if header:
		sl = [f"#### {len(sl)} datasets ####\n"] + sl
	return "\n".join(sl)

def print_datasets(iterable, names_only = False, header = True):
	"""
	Print datasets
	:param iterable: An iterable of datasets
	:param names_only: Print names only?
	:param header: Print number of datasets?
	"""
	print(format_datasets(iterable, names_only, header))

def askYesNo(msg = "Continue? (yes/no): "):
	"""
	Ask a user to confirm yes or no
	:param msg: The message to print
	:returns: True if yes, False if no
	"""
	while True:
		confirm = input(msg).casefold()
		if confirm in ("y", "yes"):
			return True
		elif confirm in ("n", "no"):
			return False
		else:
			print("Invalid input. Please enter yes/no.")

def fix_path(path, must_exist = True):
	"""
	Normalize and expand paths
	:param path: The path to normalize
	:param must_exist: Must the path exist?
	:returns: The normalized path
	"""
	if "~" in path:
		path = os.path.expanduser(path)
	path = os.path.realpath(path)
	if must_exist and not os.path.exists(path):
		raise FileNotFoundError(f"path does not exist: '{path}'")
	return path

def file_create(path):
	"""
	Create a file
	:param path: The file to create
	"""
	path = fix_path(path, must_exist=False)
	with open(path, "a"):
		os.utime(path, None)

def file_remove(path):
	"""
	Delete a file
	:param path: The file to delete
	"""
	path = fix_path(path, must_exist=False)
	if os.path.exists(path):
		os.remove(path)

def ls(path = ".", all_names = False):
	"""
	List files in a directory
	:param path: The directory
	:param all_names: Should hidden files be included?
	:returns: A list of file names
	"""
	path = fix_path(path)
	if not os.path.isdir(path):
		raise NotADirectoryError(f"path must be a directory: {path}")
	if all_names:
		return [f 
			for f 
			in os.listdir(path)]
	else:
		return [f 
			for f 
			in os.listdir(path)
			if not f.startswith(".")]

def dirsize(path, all_names = False):
	"""
	Get size of a directory
	:param path: The directory
	:param all_names: Should hidden files be included?
	:returns: The size of the directory in bytes
	"""
	size = 0
	files = ls(path, all_names=all_names)
	for file in files:
		if file in (".", ".."):
			continue
		file = os.path.join(path, file)
		if os.path.isdir(file):
			size += dirsize(file, all_names=all_names)
		else:
			size += os.path.getsize(file)
	return size

def dirfiles(path, pattern, recursive = False, all_names = False):
	"""
	Get files in a directory matching a pattern
	:param path: The directory
	:param pattern: The pattern
	:param all_names: Should hidden files be included?
	:returns: The size of the directory in bytes
	"""
	matches = []
	files = ls(path, all_names=all_names)
	for file in files:
		if file in (".", ".."):
			continue
		file = os.path.join(path, file)
		if os.path.isdir(file) and recursive:
			matches.extend(dirfiles(file, all_names=all_names))
		elif grep1(pattern, file) is not None:
			matches.append(file)
	return matches

def checkport(port):
	"""
	Check if a port is open (i.e., if it is in use)
	:param port: The port to check
	:returns: 0 if open, an error code otherwise
	"""
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	result = sock.connect_ex(("localhost", port))
	sock.close()
	return result

def findport(attempts = 10):
	"""
	Find an available port (for SSH forwarding)
	:param attempts: How many random ports to attempt
	:returns: The port number
	"""
	for i in range(attempts):
		port = random.randint(1024, 65535)
		if checkport(port) != 0:
			return port
	raise IOError("couldn't find an available port")

def grep1(pattern, x, ignore_case = True, context_width = None):
	"""
	Search for a pattern in a string
	:param pattern: The pattern to find
	:param x: A string
	:param ignore_case: Should case be ignored?
	:param context_width: Width of a context window to return
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

def grep(pattern, x, ignore_case = True):
	"""
	Search for a pattern in an iterable
	:param pattern: The pattern to find
	:param x: An iterable
	:param ignore_case: Should case be ignored?
	:returns: A list of matches
	"""
	if x is None:
		return []
	else:
		return [grep1(pattern, xi, ignore_case=ignore_case) 
			for xi 
			in x]

def grepl(pattern, x, ignore_case = True):
	"""
	Search for a pattern in an iterable
	:param pattern: The pattern to find
	:param x: An iterable
	:param ignore_case: Should case be ignored?
	:returns: A list of bools
	"""
	if x is None:
		return []
	else:
		return [match is not None 
			for match 
			in grep(pattern, x, ignore_case=ignore_case)]

