
import sys
import platform
import subprocess
import argparse
import datetime

from ..rssh import rssh
from ..tools import is_known_host
from ..tools import findport
from ..tools import badwulf_attribution

class clmanager:
	"""
	Command line utility for Beowulf clusters
	"""
	
	def __init__(self,
		name,
		nodes,
		date,
		description,
		readme = None,
		program = None,
		head = None,
		xfer = None,
		restrict = False,
		username = None,
		server = None,
		server_username = None,
		port = None):
		"""
		Initialize a cluster CLI utility program
		:param name: The name of the cluster/server
		:param nodes: A list of nodenames or dict in the form {alias: nodename}
		:param date: The date of the program's last revision
		:param description: A description of the program
		:param readme: The file path of a README.md file
		:param program: The name of the program (defaults to name)
		:param head: The head node (optional)
		:param xfer: The xfer node (optional)
		:param restrict: Should access be restricted to head/xfer nodes?
		:param username: Your username on the cluster
		:param server: The gateway server hostname (optional)
		:param server_username: Your username on the gateway server (optional)
		:param port: The local port for gateway server SSH forwarding
		"""
		self.name = name
		self.nodes = nodes
		if isinstance(self.nodes, dict):
			self.nodenames = self.nodes.values()
		else:
			self.nodenames = self.nodes
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
		self.head = head
		self.xfer = xfer
		self.restrict = restrict
		self.username = username
		self.server = server
		self.server_username = server_username
		self.port = port
		self.session = None
		self._parser = None
		self._args = None

	def _add_cluster_args(self, parser, restrict = False):
		"""
		Add cluster parameters to a parser.
		:param parser: The parser to update
		"""
		if not restrict:
			parser.add_argument("-n", "--node", action="append",
				help=f"{self.name} node", dest="nodes",
				metavar="NODE")
			if isinstance(self.nodes, dict):
				for alias, nodename in self.nodes.items():
					parser.add_argument(f"-{alias}", action="append_const",
						help=nodename, dest="nodes", const=nodename)
		if self.head is not None:
			parser.add_argument("-H", "--head", action="append_const",
				help=f"{self.name} head node ({self.head})",
				dest="nodes", const=self.head)
		if self.xfer is not None:
			parser.add_argument("-x", "--xfer", action="append_const",
				help=f"{self.name} xfer node ({self.xfer})",
				dest="nodes", const=self.xfer)
		parser.add_argument("-u", "--user", action="store",
			help=f"{self.name} user (default: {self.username})",
			default=self.username)
		parser.add_argument("-p", "--port", action="store",
			help="port forwarding", default=self.port)
		parser.add_argument("-L", "--login", action="store",
			help=f"gateway server user (default: {self.server_username})",
			default=self.server_username)
		parser.add_argument("-S", "--server", action="store",
			help=f"gateway server host (default: {self.server})",
			default=self.server)
	
	def _add_subcommand_run(self, subparsers):
		"""
		Add 'run' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("run", 
			help=f"run command (e.g., shell) on a {self.name} node")
		self._add_cluster_args(cmd, restrict=self.is_restricted_client())
		cmd.add_argument("remote_command", action="store",
			help="command to execute on a Magi node",
			nargs=argparse.OPTIONAL,
			metavar="command")
		cmd.add_argument("remote_args", action="store",
			help="command arguments",
			nargs=argparse.REMAINDER,
			metavar="...")
	
	def _add_subcommand_copy_id(self, subparsers):
		"""
		Add 'copy-id' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("copy-id", 
			help=f"copy ssh keys to a {self.name} node")
		self._add_cluster_args(cmd, restrict=self.is_restricted_client())
		cmd.add_argument("identity_file", action="store",
			help="ssh key identity file")
	
	def _add_subcommand_upload(self, subparsers):
		"""
		Add a 'upload' subcommand to subparsers.
		:param subparsers: The subparsers to update
		"""
		cmd = subparsers.add_parser("upload", 
			help=f"upload file(s) to {self.name}")
		self._add_cluster_args(cmd, restrict=self.is_restricted_client())
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
		self._add_cluster_args(cmd, restrict=self.is_restricted_client())
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
	
	def is_client(self):
		"""
		Check if the program is running on a remote client
		:returns: True if running on a remote client, False otherwise
		"""
		return not is_known_host(self.nodenames)
	
	def is_restricted_client(self):
		"""
		Check if the program is running on a restricted remote client
		:returns: True if nodes should be restricted, False otherwise
		"""
		return self.is_client() and self.restrict

	def is_node(self):
		"""
		Check if the program is running on a cluster node
		:returns: True if running on a cluster node, False otherwise
		"""
		return is_known_host(self.nodenames)
	
	def resolve_node(self, nodes):
		"""
		Get a single valid nodenames from a list of nodes
		:param nodes: A list of nodenames
		:returns: A single nodename
		"""
		if nodes is None or len(nodes) != 1:
			sys.exit(f"{self.program}: error: must specify exactly _one_ {self.name} node")
		return self.resolve_nodes(nodes)[0]
	
	def resolve_nodes(self, nodes):
		"""
		Get one or more valid nodenames from a list of nodes
		:param nodes: A list of nodenames
		:returns: A list of nodenames
		"""
		if nodes is None or len(nodes) < 1:
			sys.exit(f"{self.program}: error: must specify at least _one_ {self.name} node")
		nodenames = [node.casefold() for node in self.nodenames]
		localhost = platform.node().replace(".local", "")
		hosts = []
		for node in nodes:
			if node.casefold() not in nodenames:
				sys.exit(f"{self.program}: error: {node} is not a valid {self.name} node")
			if self.is_node():
				if node.casefold() == localhost:
					node = "localhost"
				else:
					node += ".local"
			hosts.append(node)
		return hosts
	
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
		self.session = rssh(username, node,
			server=server,
			server_username=server_username,
			port=port,
			autoconnect=False)
		return self.session
	
	def run(self,
		node,
		command = None,
		arglist = None):
		"""
		Run a command on a cluster node
		:param node: The cluster node
		:param command: The command to run
		:param arglist: The command arguments
		:returns: A subprocess instance
		"""
		con = self.session
		if node is not None:
			con.destination = node
		if arglist is None:
			arglist = []
		if command is None:
			return con.ssh()
		elif node == "localhost":
			cmd = [command] + arglist
			return subprocess.run(cmd)
		else:
			print(f"connecting as {con.username}@{con.destination}")
			dest = f"{con.username}@{con.hostname}"
			if con.server is None:
				cmd = ["ssh", dest]
			else:
				cmd = ["ssh", "-o", "NoHostAuthenticationForLocalhost=yes"]
				cmd += ["-p", str(con.port), dest]
			cmd.append(command)
			cmd.extend(arglist)
			return subprocess.run(cmd)
	
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
			print(f"{description} (revised {self.date})")
			print(badwulf_attribution())
			sys.exit()
		# help
		if args.cmd is None:
			self._parser.print_help()
		# readme
		elif args.cmd == "readme":
			if args.pager is None:
				cmd = ["glow", "-p", "-w", str(args.width)]
			else:
				cmd = [args.pager]
			cmd += [self.readme]
			subprocess.run(cmd)
		# ...
		else:
			self.username = args.user
			self.server = args.server
			self.server_username = args.login
			self.port = args.port
		# run
		if args.cmd == "run":
			hosts = self.resolve_nodes(args.nodes)
			for host in hosts:
				self.run(host, args.remote_command, args.remote_args)
		# copy-id
		elif args.cmd == "copy-id":
			hosts = self.resolve_nodes(args.nodes)
			for host in hosts:
				self.session.destination = host
				self.session.copy_id(args.identity_file)
		# upload
		elif args.cmd == "upload":
			self.session.destination = self.resolve_node(args.nodes)
			self.session.upload(args.src, args.dest,
				dry_run=args.dry_run, ask=args.ask)
		# download
		elif args.cmd == "download":
			self.session.destination = self.resolve_node(args.nodes)
			self.session.download(args.src, args.dest,
				dry_run=args.dry_run, ask=args.ask)
		sys.exit()
