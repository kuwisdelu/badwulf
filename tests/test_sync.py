
import os
import json
import tempfile

from badwulf.sync import syncer

def _testconfig():
	try:
		return os.path.join(os.path.dirname(__file__), 
			"tests", "testfiles", "badwulf-sites.json")
	except NameError:
		return os.path.join("..", 
			"tests", "testfiles", "badwulf-sites.json")

def test_syncer():
	c1 = syncer.from_path(_testconfig())
	c2 = syncer.from_dict(c1.to_dict())
	assert c1.to_dict() == c2.to_dict()
