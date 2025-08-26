#!/usr/bin/env python3

from badwulf.cli import dbmanager

wulfdb = dbmanager("Badwulf DB", 
	dbpath="examples/exampledb",
	dbname=None,
	date = "2025-08-26",
	description = "Badwulf database CLI utility",
	program = "wulfdb")

wulfdb.main()
