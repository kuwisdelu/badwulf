# Badwulf 

## Minimal manager for Beowulf clusters and scientific data

The goal of *badwulf* is a provide a minimal command line interface for accessing and managing experimental data on scientific computing servers and Beowulf clusters.

This tool is __not__ intended to replace true cluster management and scheduling software for such as *Slurm*. Instead, *badwulf* is a lightweight package for simplying tasks such as:

- Connecting an port forwarded SSH session to a research server behind a login server

- Transfering files and directories between a local client and a research server

- Managing a simple repository of experimental data and metadata

- Searching experimental metadata for terms and keywords

- Syncing experimental data between a local client and a research server

## Examples

A command line utility named `wulf` for a hypothetical "Badwulf" cluster with compute nodes named "Wulf-01", "Wulf-02", and "Wulf-03" could be set up as follows:

```
#!/usr/bin/env python3

import os
from badwulf.cli import clmanager

wulf = clmanager("Badwulf",
	nodes = {
		"01": "Wulf-01",
		"02": "Wulf-02",
		"03": "Wulf-03"},
	version = "0.0.0",
	date = "2024-12-27",
	description = "Badwulf CLI utility",
	username = os.getenv("BADWULF_USER"),
	server = os.getenv("BADWULF_SERVER"),
	server_username = os.getenv("BADWULF_LOGIN"),
	program = "wulf")

wulf.main()
```

This would read the environment variables `$BADWULF_USER`, `$BADWULF_SERVER`, and `$BADWULF_LOGIN` to set up the SSH connection to the cluster.

A user could then connect to the node "Wulf-01" as:

```
wulf run -01
```
