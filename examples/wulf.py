#!/usr/bin/env python3

from badwulf.cli import clmanager

wulf = clmanager("Badwulf",
	nodes = {
		"01": "Wulf-01",
		"02": "Wulf-02",
		"03": "Wulf-03"},
	version = "0.0.0",
	date = "2024-12-27",
	description = "Badwulf CLI utility",
	program = "wulf")

wulf.main()
