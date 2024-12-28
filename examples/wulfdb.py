#!/usr/bin/env python3

from badwulf.cli import dbmanager

wulfdb = dbmanager("Badwulf DB", "/Volumes/Datasets", None,
	version = "0.0.0",
	date = "2024-12-27",
	description = "Badwulf database CLI utility",
	program = "wulfdb")

wulfdb.main()
