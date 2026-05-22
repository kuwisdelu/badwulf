
import pytest
import os
import tomllib
import tempfile

from badwulf.db import expdata

def _testdb():
	try:
		return os.path.join(os.path.dirname(__file__), "tests", "testdb")
	except NameError:
		return os.path.join("..", "tests", "testdb")

def test_expdata_meta_search():
	p = ("public", "Example", "example0")
	e = expdata.from_path(os.path.join(_testdb(), *p))
	assert e.size == e.meta_size
	with open(os.path.join(path, "metadata.toml"), "rb") as f:
		d = tomllib.load(f)
	assert e.meta.to_dict() == d
	assert e.meta.has_scope("public")
	assert e.meta.has_group("Example")
	assert not e.meta.has_scope("private")
	assert not e.meta.has_group("Bad Wolf Corporation")
	s1 = e.meta.search("bad wolf")
	s2 = e.meta.search("bad")
	s3 = e.meta.search("Rose")
	assert s1.hits == {"contact": [{"name": "Bad Wolf"}]}
	assert "contact" in s2.hits and "url" in s2.hits
	assert s3 is None

def test_expdata_move_copy_unlink():
	p = ("public", "Example", "example0")
	e = expdata.from_path(os.path.join(_testdb(), *p))
	with tempfile.TemporaryDirectory() as tmp:
		dst_cp = os.path.join(tmp, "cp", *p)
		dst_mv = os.path.join(tmp, "mv", *p)
		e2 = e.copy(dst_cp)
		assert os.path.exists(e.path)
		assert os.path.exists(e2.path)
		assert e2.path != e.path
		assert e2.meta == e.meta
		assert e2.meta_size == e.meta_size
		e2.move(dst_mv)
		assert not os.path.exists(dst_cp)
		assert os.path.exists(e2.path)
		assert e2.path != e.path
		assert e2.meta == e.meta
		assert e2.meta_size == e.meta_size
		e2.unlink()
		assert not os.path.exists(e2.path)
		assert os.path.exists(e.path)
