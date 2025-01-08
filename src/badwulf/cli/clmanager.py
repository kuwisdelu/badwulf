
import sys
import platform
import subprocess
import argparse
import datetime
from time import sleep

from ..rssh import rssh
from ..tools import badwulf_attribution
from ..tools import is_known_host
from ..tools import findport

class clmanager:
	"""
	Command line utility for Beowulf clusters
	"""
	
	def __init__(self,
		name,
		nodes,
		version,
		date,
		description,
		readme = None,
		program = None,
		username = None,
		server = None,
		server_username = False,
		port = None):
		"""
		Initialize a cluster CLI utility program
		:param name: The name of the cluster/server
		:param nodes: A list of nodenames or dict in the form {alias: nodename}
		:param version: The version of the program
		:param date: The date of the program's last revision
		:param description: A description of the program
		:param readme: The file path of a README.md file
		:param program: The name of the program (defaults to name)
		:param username: Your username on the cluster
		:param server: The gateway server hostname (optional)
		:param server_username: Your username on the gateway server (optional)
		:param port: The local port for gateway server SSH forwarding
		"""
		self.name = name
		self.nodes = nodes
		self.version = version
		if isinstance(date, datetime.date):
			self.date = date
		else:
			self.date = datetime.date.fromisoformat(date)
		self.description = description
		self.readme = readme
		if program is None:
			self.program = name.casefold()
		else:
			self.program = program
		self.username = username
		self.server = server
		self.server_username = server_username
		self.port = port
		self._parser = None
		self._args = None

	def _add_cluster_args(self, parser):
		"""
		Add cluster parameters to a parser.
		:param parser: The parser to update
		"""
		if isinstance(self.nodes, dict):
			for alias, nodename in self.nodes.items():
				parser.add_argument(f"-{alias}", action="append_const",
					help=nodename, dest="nodes", const=nodename)
		parser.add_argument("-n", "--node", action="append",
			help=f"{self.name} node", dest="nodes",
			metavar="NODE")
		parser.add_argument("-p", "--port", action="store",
			help="port forwarding", default=self.port)
		parser.add_argument("-u", "--user", action="store",
			help=f"{self.name} user", default=self.username)
		parser.add_argument("-L", "--login", action="store",
			help="gateway server user", default=self.server_username)
		parser.add_argument("-S", "--server", action="store",
			help="gateway server host", default=self.server)
	
	def _add_subcommand_run(self, subparsers):
		"""
		Add 'run' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("run", 
			help=f"run command (e.g., shell) on a {self.name} node")
		self._add_cluster_args(cmd)
		cmd.add_argument("remote_command", action="store",
			help="command to execute on a Magi node", nargs=argparse.OPTIONAL,
			metavar="command")
		cmd.add_argument("remote_args", action="store",
			help="command arguments", nargs=argparse.REMAINDER,
			metavar="...")
	
	def _add_subcommand_copy_id(self, subparsers):
		"""
		Add 'copy-id' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("copy-id", 
			help=f"copy ssh keys to a {self.name} node")
		self._add_cluster_args(cmd)
		cmd.add_argument("identity_file", action="store",
			help="ssh key identity file")
	
	def _add_subcommand_upload(self, subparsers):
		"""
		Add a 'upload' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("upload", 
			help=f"upload file(s) to {self.name}")
		self._add_cluster_args(cmd)
		cmd.add_argument("src", action="store",
			help="source file/directory")
		cmd.add_argument("dest", action="store",
			help="destination file/directory")
		cmd.add_argument("--ask", action="store_true",
			help="ask to confirm before uploading files?")
		cmd.add_argument("--dry-run", action="store_true",
			help="show what would happen without doing it?")
	
	def _add_subcommand_download(self, subparsers):
		"""
		Add a 'download' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("download", 
			help=f"download file(s) from {self.name}")
		self._add_cluster_args(cmd)
		cmd.add_argument("src", action="store",
			help="source file/directory")
		cmd.add_argument("dest", action="store",
			help="destination file/directory")
		cmd.add_argument("--ask", action="store_true",
			help="ask to confirm before downloading files?")
		cmd.add_argument("--dry-run", action="store_true",
			help="show what would happen without doing it?")
	
	def _add_subcommand_readme(self, subparsers):
		"""
		Add 'readme' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("readme", 
			help="display readme")
		cmd.add_argument("-p", "--pager", action="store",
			help="program to display readme (default 'glow')")
		cmd.add_argument("-w", "--width", action="store",
			help="word-wrap readme at width (default 70)", default=70)

	def _init_parser(self):
		"""
		Initialize the argument parser
		"""
		parser = argparse.ArgumentParser(self.program,
			description=self.description)
		parser.add_argument("-v", "--version", action="store_true",
			help="display version")
		subparsers = parser.add_subparsers(dest="cmd")
		self._add_subcommand_run(subparsers)
		self._add_subcommand_copy_id(subparsers)
		self._add_subcommand_upload(subparsers)
		self._add_subcommand_download(subparsers)
		if self.readme is not None:
			self._add_subcommand_readme(subparsers)
		self._parser = parser
	
	def is_node(self):
		"""
		Check if the program is running on a cluster node
		:returns: True if running the a cluster node, False otherwise
		"""
		if isinstance(self.nodes, dict):
			nodes = self.nodes.values()
		else:
			nodes = self.nodes
		return is_known_host(nodes)
	
	def resolve_node(self, nodes):
		"""
		Get single valid nodename from a list of nodes
		:param nodes: A list of nodenames
		"""
		host = platform.node().replace(".local", "")
		if nodes is None or len(nodes) != 1:
			sys.exit(f"{self.program}: error: must specify exactly _one_ {self.name} node")
		node = nodes[0]
		if self.is_node():
			if host == node.casefold():
				node = "localhost"
			else:
				node += ".local"
		return node
	
	def open_ssh(self,
		node,
		username = None,
		server = None,
		server_username = None,
		port = None):
		"""
		Open SSH connection to a cluster node
		:param node: The target cluster node
		:param username: Your username on the cluster
		:param server: The gateway server hostname (optional)
		:param server_username: Your username on the gateway server (optional)
		:param port: Port used for gateway forwarding
		:returns: An open rssh instance
		"""
		if username is None:
			username = self.username
		if server is None:
			server = self.server
		if server_username is None:
			server_username = self.server_username
		if port is None:
			port = findport()
		# connect and return the session
		session = rssh(username, node,
			server=server,
			server_username=server_username,
			port=port,
			autoconnect=True)
		return session
	
	def parse_args(self):
		"""
		Parse command line arguments
		"""
		if self._parser is None:
			self._init_parser()
		self._args = self._parser.parse_args()
	
	def main(self):
		"""
		Run the program
		"""
		if self._args is None:
			self.parse_args()
		args = self._args
		# version
		if args.version:
			description = self.description.splitlines()[0]
			print(f"{description} version {self.version} (revised {self.date})")
			print(badwulf_attribution())
			sys.exit()
		# open ssh for server commands
		if args.cmd in ("run", "copy-id", "upload", "download"):
			con = self.open_ssh(self.resolve_node(args.nodes),
				username=args.user,
				server=args.server,
				server_username=args.login, 
				port=args.port)
			sleep(1) # allow time to connect
		# help
		if args.cmd is None:
			self._parser.print_help()
		# run
		elif args.cmd == "run":
			if args.remote_command is None:
				con.ssh()
			else:
				print(f"connecting as {con.username}@{con.destination}")
				dest = f"{con.username}@{con.hostname}"
				if con.server is None:
					cmd = ["ssh", dest]
				else:
					cmd = ["ssh", "-o", "NoHostAuthenticationForLocalhost=yes"]
					cmd += ["-p", str(con.port), dest]
				cmd.append(args.remote_command)
				cmd.extend(args.remote_args)
				subprocess.run(cmd)
		# copy-id
		elif args.cmd == "copy-id":
			con.copy_id(args.identity_file)
		# upload
		elif args.cmd == "upload":
			con.upload(args.src, args.dest,
				dry_run=args.dry_run, ask=args.ask)
		# download
		elif args.cmd == "download":
			con.download(args.src, args.dest,
				dry_run=args.dry_run, ask=args.ask)
		# readme
		elif args.cmd == "readme":
			if args.pager is None:
				cmd = ["glow", "-p", "-w", str(args.width)]
			else:
				cmd = [args.pager]
			cmd += [self.readme]
			subprocess.run(cmd)
		sys.exit()
