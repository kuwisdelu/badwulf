
import pytest
import os
import sys
if sys.version_info >= (3, 11):
	import tomllib
else:
	import tomli as tomllib

from badwulf.db import expmeta
from badwulf.db import expdata
from badwulf.db import expdb

def test_expmeta_expdata_expsearch():
	root = globals().get("__file__", "..")
	path = os.path.join(root, "tests", "testdb", 
		"public", "Example", "example0")
	e = expdata.from_path(path)
	m = e.meta
	assert isinstance(e, expdata)
	assert isinstance(m, expmeta)
	assert e.meta_size == e.tree_size
	with open(os.path.join(path, "metadata.toml"), "rb") as f:
		d = tomllib.load(f)
	assert m.to_dict() == d
	assert m.has_scope("public")
	assert m.has_group("Example")
	assert not m.has_scope("private")
	assert not m.has_group("Bad Wolf Corporation")
	s1 = e.meta.search("bad wolf")
	s2 = e.meta.search("bad")
	s3 = e.meta.search("Rose")
	assert s1.hits == {"contact": [{"name": "Bad Wolf"}]}
	assert "contact" in s2.hits and "url" in s2.hits
	assert s3 is None
