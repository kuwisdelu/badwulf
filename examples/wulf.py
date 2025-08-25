#!/usr/bin/env python3

from badwulf.cli import clmanager

wulf = clmanager("Badwulf",
	nodes = {
		"01": "Wulf-01",
		"02": "Wulf-02",
		"03": "Wulf-03"},
	date = "2025-08-26",
	description = "Badwulf CLI utility",
	program = "wulf")

wulf.main()
