
# Restricted SSH manager

import os
import subprocess
from time import sleep
from dataclasses import dataclass
from dataclasses import asdict

from .tools import fix_path
from .tools import confirm
from .tools import quote
from .tools import findport

@dataclass
class rssh:
	"""
	Restricted SSH manager for rsync
	:ivar user: Username for the destination
	:ivar host: Hostname for the destination
	:ivar port: Destination's SSH port 
	:ivar proxy_user: (Optional) Proxy jump username
	:ivar proxy_host: (Optional) Proxy jump hostname
	:ivar proxy_port: (Optional) Local port for forwarding
	:ivar process: An open subprocess for port forwarding
	"""
	user: str 
	host: str 
	port: int = 22 
	proxy_user: str | None = None 
	proxy_host: str | None = None 
	proxy_port: int | None = None 
	process: subprocess.Popen | None = None 

	def __post_init__(self):
		if self.proxy_user is not None and self.proxy_host is None:
			raise TypeError("proxy_user provided but proxy_host is None")
		if self.proxy_host is not None and self.proxy_user is None:
			raise TypeError("proxy_host provided but proxy_user is None")
		if self.proxy_host is not None:
			if self.proxy_port is None:
				self.proxy_port = findport()

	def __enter__(self) -> rssh:
		"""
		Enter context manager
		"""
		self.open()
		return self
	
	def __exit__(self, exc_type, exc_value, traceback):
		"""
		Exit context manager
		"""
		self.close()
	
	def __del__(self) -> None:
		"""
		Delete self
		"""
		self.close()
	
	@property
	def rsh(self) -> list[str]:
		"""
		Get the SSH program prefix list
		"""
		rsh = ["ssh"]
		if self.has_proxy_jump():
			if self.is_open():
				rsh += ["-o", "NoHostAuthenticationForLocalhost=yes"]
				rsh += ["-o", f"Port={self.proxy_port}"]
			else:
				rsh += ["-o", f"ProxyJump={self.proxy_destination}"]
		return rsh

	@property
	def destination(self) -> str:
		"""
		Get the resolved destination
		"""
		user = self.user
		if user != "":
			user += "@"
		if self.is_open():
			return f"{user}localhost"
		else:
			return f"{user}{self.host}"

	@property
	def proxy_destination(self) -> str | None:
		"""
		Get the resolved proxy destination
		"""
		if self.has_proxy_jump():
			user = self.proxy_user
			if user != "":
				user += "@"
			return f"{user}{self.proxy_host}"
		else:
			return None

	def has_proxy_jump(self) -> bool:
		"""
		Check if the connection requires a proxy jump
		"""
		return self.proxy_host is not None

	def is_open(self) -> bool:
		"""
		Check if the proxy jump connection is open
		"""
		return self.process is not None

	def open(self) -> None:
		"""
		Open port forwarding through proxy jump host (if applicable)
		"""
		if self.has_proxy_jump() and not self.is_open():
			forward = f"{self.proxy_port}:{self.host}:{self.port}"
			cmd = ["ssh", "-NL", forward, self.proxy_destination]
			self.process = subprocess.Popen(cmd)
			sleep(1) # allow time to connect

	def close(self) -> None:
		"""
		Close port forwarding through proxy jump host (if applicable)
		"""
		if self.has_proxy_jump() and self.is_open():
			self.process.terminate()
		if self.process is not None:
			self.process = None
	
	def is_batch(self) -> bool:
		"""
		Check if connection can be established without prompts
		"""
		cmd = self.rsh + ["-o", "BatchMode=yes"] 
		cmd += [self.destination, "true"]
		proc = subprocess.run(cmd)
		return proc.returncode == 0
	
	def ls(self, 
		path: str | list[str] | None = None, 
		all_names: bool = False, 
		details: bool = False) -> subprocess.CompletedProcess:
		"""
		List files on the destination machine
		:param path: A file or directory or list of them
		:param all_names: Should hidden files be included?
		:param details: Show file metadata details?
		"""
		cmd = self.rsh 
		cmd += [self.destination, "ls"]
		if all_names:
			cmd += ["-a"]
		if details:
			cmd += ["-l"]
		if path is not None:
			if isinstance(path, str):
				cmd += [path]
			else:
				cmd += path
		return subprocess.run(cmd)

	def push(self, 
		src: str, 
		dst: str, 
		mirror: bool = False,
		dry_run: bool = False, 
		ask: bool = False):
		"""
		Push file/directory from src to dst using rsync
		:param src: The source path on localhost
		:param dst: The destination path on target host
		:param mirror: Delete files in dst that aren't in src?
		:param dry_run: Show what would be done without doing it?
		:param ask: Confirm before pushing?
		"""
		if src[-1] == "/":
			src = fix_path(src, must_exist=True)
			if src[-1] != "/":
				src += "/"
		else:
			src = fix_path(src, must_exist=True)
		dst = f"{self.destination}:{quote(dst)}"
		cmd = ["rsync", "-aP"]
		if mirror:
			cmd += ["--delete"]
		if dry_run:
			cmd += ["--dry-run"]
		if self.has_proxy_jump():
			cmd += ["-e", " ".join(self.rsh)]
		cmd += [src, dst]
		if ask:
			print(f"Data will be pushed from: '{src}'")
			print(f"Data will be pushed to: '{dst}'")
			print("The following command will be run:")
			print(" ".join(cmd))
			if not confirm("Continue?"):
				return
		return subprocess.run(cmd)

	def pull(self, 
		src: str, 
		dst: str, 
		mirror: bool = False,
		dry_run: bool = False, 
		ask: bool = False):
		"""
		Pull file/directory from src to dst using rsync
		:param src: The source path on target host
		:param dst: The destination path on localhost
		:param mirror: Delete files in dst that aren't in src?
		:param dry_run: Show what would be done without doing it?
		:param ask: Confirm before pushing?
		"""
		src = f"{self.destination}:{quote(src)}"
		if dst[-1] == "/":
			dst = fix_path(dst, must_exist=False)
			if dst[-1] != "/":
				dst += "/"
		else:
			dst = fix_path(dst, must_exist=False)
		cmd = ["rsync", "-aP"]
		if mirror:
			cmd += ["--delete"]
		if dry_run:
			cmd += ["--dry-run"]
		if self.has_proxy_jump():
			cmd += ["-e", " ".join(self.rsh)]
		cmd += [src, dst]
		if ask:
			print(f"Data will be pulled from: '{src}'")
			print(f"Data will be pulled to: '{dst}'")
			print("The following command will be run:")
			print(" ".join(cmd))
			if not confirm("Continue?"):
				return
		return subprocess.run(cmd)
	
	def ssh(self):
		"""
		Attach an unrestricted ssh terminal session
		"""
		cmd = self.rsh + [self.destination]
		return subprocess.run(cmd)
