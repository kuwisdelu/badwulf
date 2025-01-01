
# Restricted SSH manager

import subprocess

from .tools import fix_path
from .tools import askYesNo

class rssh:
	"""
	Restricted SSH manager for rsync
	"""
	
	def __init__(self, username, destination,
		server = None, server_username = True,
		port = 8080, destination_port = 22,
		autoconnect = True):
		"""
		Initialize an rssh instance
		:param username: Your username on destination machine
		:param destination: The destination machine hostname
		:param server: The gateway server hostname (optional)
		:param server_username: Your username on the gateway server (optional)
		:param port: The local port for gateway server SSH forwarding
		:param destination_port: The destination port
		:param autoconnect: Connect on initialization?
		"""
		if server_username in (True, False):
			if server_username:
				server_username = username
			else:
				server_username = ""
		self.username = username
		self.destination = destination
		self.server = server
		self.server_username = server_username
		self.port = port
		self.destination_port = destination_port
		self.process = None
		if autoconnect:
			self.open()
	
	def __str__(self):
		"""
		Return str(self)
		"""
		dest = f"{self.username}@{self.destination}"
		if self.isopen():
			server = f"(forwarding to {self.server} over {self.port})"
			return "ssh: " + dest + " " + server
		else:
			return "ssh: " + dest
	
	def __repr__(self):
		"""
		Return repr(self)
		"""
		user = f"username='{self.username}'"
		dest = f"destination='{self.destination}'"
		if self.isopen():
			server = f"server='{self.server}'"
			server_username = f"server_username='{self.server_username}'"
			port = f"port={self.port}"
			return f"rssh({user}, {dest}, {server}, {server_username}, {port})"
		else:
			return f"rssh({user}, {dest})"
	
	def __enter__(self):
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
	
	def __del__(self):
		"""
		Delete self
		"""
		self.close()
	
	@property
	def hostname(self):
		"""
		Get the hostname used for the SSH connection
		"""
		if self.server is None:
			return self.destination
		else:
			return "localhost"
	
	def isopen(self):
		"""
		Check if the gateway server connection is open
		"""
		return self.process is not None

	def open(self):
		"""
		Open the connection to the gateway server
		"""
		if self.server is None or self.isopen():
			return
		print(f"opening connection to {self.server}")
		if not isinstance(self.server_username, str):
			msg = "Please enter your username: "
			self.server_username = input(msg)
		if len(self.server_username) == 0:
			gateway = self.server
		else:
			gateway = f"{self.server_username}@{self.server}"
		target = f"{self.port}:{self.destination}:{self.destination_port}"
		cmd = ["ssh", "-NL", target, gateway]
		try:
			print(f"connecting as {gateway}")
			self.process = subprocess.Popen(cmd)
			print(f"forwarding to {self.destination} on port {self.port}")
		except Exception:
			self.process = None
			print("failed to open connection")
	
	def ls(self, file = None, all_names = False, details = False):
		"""
		List files on the destination machine
		:param file: A file or directory or list of them
		:param all_names: Should hidden files be included?
		:param details: Show file metadata details?
		"""
		host = f"{self.username}@{self.hostname}"
		if self.server is None:
			cmd = ["ssh", host]
		else:
			cmd = ["ssh", "-o", "NoHostAuthenticationForLocalhost=yes"]
			cmd += ["-p", str(self.port), host]
		cmd += ["ls"]
		if all_names:
			cmd += ["-a"]
		if details:
			cmd += ["-l"]
		if file is not None:
			if isinstance(file, str):
				cmd += [file]
			else:
				cmd += file
		print(f"connecting as {self.username}@{self.destination}")
		return subprocess.run(cmd)
	
	def copy_id(self, id_file, ask = False):
		"""
		Copy local SSH keys to the destination machine
		:param id_file: The identity file (ending in .pub)
		:param ask: Confirm before copying?
		"""
		truehost = f"{self.username}@{self.hostname}"
		showhost = f"{self.username}@{self.destination}"
		id_file = fix_path(id_file, must_exist=True)
		print(f"key will be uploaded from: '{id_file}'")
		print(f"key will be uploaded to: '{showhost}'")
		if ask and not askYesNo():
			return
		print(f"copying key as {showhost}")
		cmd = ["ssh-copy-id", "-i", id_file]
		if self.server is None:
			cmd += [truehost]
		else:
			cmd += ["-o", "NoHostAuthenticationForLocalhost=yes"]
			cmd += ["-p", str(self.port)]
			cmd += [truehost]
		return subprocess.run(cmd)
	
	def download(self, src, dest, dry_run = False, ask = False):
		"""
		Download file(s) to local storage using rsync
		:param src: The source path on the destination machine
		:param dest: The destination path on the local machine
		:param dry_run: Show what would be done without doing it?
		:param ask: Confirm before downloading?
		"""
		truesrc = f"{self.username}@{self.hostname}:{src}"
		showsrc = f"{self.username}@{self.destination}:{src}"
		has_trailing_slash = dest[-1] == "/"
		dest = fix_path(dest, must_exist=False)
		if dest[-1] != "/" and has_trailing_slash:
			dest += "/"
		print(f"data will be downloaded from: '{showsrc}'")
		print(f"data will be downloaded to: '{dest}'")
		if ask and not askYesNo():
			return
		print(f"downloading data as {self.username}@{self.destination}")
		if self.server is None:
			cmd = ["rsync", "-aP", truesrc, dest]
		else:
			rsh = ["ssh", "-o", "NoHostAuthenticationForLocalhost=yes"]
			rsh = " ".join(rsh + ["-p", str(self.port)])
			cmd = ["rsync", "-aP", "--rsh", rsh, truesrc, dest]
		if dry_run:
			cmd += ["--dry-run"]
		return subprocess.run(cmd)
	
	def upload(self, src, dest, dry_run = False, ask = False):
		"""
		Upload file(s) from local storage using rsync
		:param src: The source path on the local machine
		:param dest: The destination path on the destination machine
		:param dry_run: Show what would be done without doing it?
		:param ask: Confirm before uploading?
		"""
		truedest = f"{self.username}@{self.hostname}:{dest}"
		showdest = f"{self.username}@{self.destination}:{dest}"
		has_trailing_slash = src[-1] == "/"
		src = fix_path(src, must_exist=True)
		if src[-1] != "/" and has_trailing_slash:
			src += "/"
		print(f"data will be uploaded from: '{src}'")
		print(f"data will be uploaded to: '{showdest}'")
		if ask and not askYesNo():
			return
		print(f"uploading data as {self.username}@{self.destination}")
		if self.server is None:
			cmd = ["rsync", "-aP", src, truedest]
		else:
			rsh = ["ssh", "-o", "NoHostAuthenticationForLocalhost=yes"]
			rsh = " ".join(rsh + ["-p", str(self.port)])
			cmd = ["rsync", "-aP", "--rsh", rsh, src, truedest]
		if dry_run:
			cmd += ["--dry-run"]
		return subprocess.run(cmd)
	
	def ssh(self):
		"""
		Attach an unrestricted ssh terminal session
		"""
		print(f"connecting as {self.username}@{self.destination}")
		dest = f"{self.username}@{self.hostname}"
		if self.server is None:
			cmd = ["ssh", dest]
		else:
			cmd = ["ssh", "-o", "NoHostAuthenticationForLocalhost=yes"]
			cmd += ["-p", str(self.port), dest]
		return subprocess.run(cmd)
	
	def close(self):
		"""
		Close the connection to the gateway server
		"""
		if self.process is None:
			return
		print(f"closing connection to {self.server}")
		self.process.terminate()
		self.process = None

