
import os
import tomllib
import tempfile
import shutil

from badwulf.db import expdata
from badwulf.db import expindex
from badwulf.db import expdb

def _testindex():
	try:
		return os.path.join(os.path.dirname(__file__), 
			"tests", "testfiles", "manifest.json")
	except NameError:
		return os.path.join("..", 
			"tests", "testfiles", "manifest.json")

def _testdb():
	try:
		return os.path.join(os.path.dirname(__file__), "tests", "testdb")
	except NameError:
		return os.path.join("..", "tests", "testdb")

def test_expdata_meta_search():
	p = ("public", "Example", "example0")
	e = expdata.from_path(os.path.join(_testdb(), *p))
	assert e.is_local()
	assert e.size == e.meta_size
	with open(os.path.join(_testdb(), *p, "metadata.toml"), "rb") as f:
		m = tomllib.load(f)
	assert e.meta.to_dict() == m
	assert e.meta.has_scope("public")
	assert e.meta.has_group("Example")
	assert not e.meta.has_scope("private")
	assert not e.meta.has_group("Bad Wolf Corporation")
	s1 = e.meta.search("bad wolf", ignore_case=True)
	s2 = e.meta.search("Bad")
	s3 = e.meta.search("Rose")
	s4 = e.meta.search("example")
	s5 = e.meta.search("example", within={"keywords"})
	assert s1.hits == {"contact": [{"name": "Bad Wolf"}]}
	assert "contact" in s2.hits
	assert s3 is None
	assert set(s4.hits.keys()) == {"name", "title", "keywords"}
	assert set(s5.hits.keys()) == {"keywords"}
	d = e.to_dict()
	assert expdata.from_dict(d) == e

def test_expdata_move_copy_unlink():
	p = ("public", "Example", "example0")
	e = expdata.from_path(os.path.join(_testdb(), *p))
	td = tempfile.TemporaryDirectory()
	dst_cp = os.path.join(td.name, "test-cp", *p)
	dst_mv = os.path.join(td.name, "test-mv", *p)
	dst_db = os.path.join(td.name, "test-db")
	e2 = e.copy(dst_cp)
	assert e2.is_local()
	assert os.path.exists(e.path)
	assert os.path.exists(e2.path)
	assert e2.path != e.path
	assert e2.meta == e.meta
	assert e2.meta_size == e.meta_size
	assert e2.is_misplaced_under(dst_db)
	e2.move(dst_mv)
	assert e2.is_local()
	assert not os.path.exists(dst_cp)
	assert os.path.exists(e2.path)
	assert e2.path != e.path
	assert e2.meta == e.meta
	assert e2.meta_size == e.meta_size
	assert e2.is_misplaced_under(dst_db)
	e2.place_under(dst_db)
	assert not e2.is_misplaced_under(dst_db)
	assert os.path.exists(e2.path)
	e2.unlink()
	assert not os.path.exists(e2.path)
	assert os.path.exists(e.path)
	td.cleanup()

def test_expindex():
	d = expindex.from_path(_testindex())
	assert "example0" in d
	assert isinstance(d["example0"], expdata)
	assert [k for k, v, in d.items()] == list(d.keys())
	assert [v for k, v, in d.items()] == list(d.values())
	assert not d["example0"].is_local()
	sizes1 = [e.size for e in d.sorted_by("size")]
	sizes2 = [e.size for e in d.sorted_by("size", reverse=True)]
	assert sizes1 == sorted(sizes1)
	assert sizes2 == sorted(sizes2, reverse=True)
	mtimes1 = [e.mtime for e in d.sorted_by("mtime")]
	mtimes2 = [e.mtime for e in d.sorted_by("mtime", reverse=True)]
	assert mtimes1 == sorted(mtimes1)
	assert mtimes2 == sorted(mtimes2, reverse=True)
	assert len(d.subset({"data0", "data1"})) == 2
	assert len(d.subset(scope={"public"})) == 1
	assert len(d.subset(scope={"private"})) == 4
	assert len(d.subset({"data0"}, scope={"public"})) == 0
	assert len(d.subset({"data0"}, scope={"private"})) == 1
	assert len(d.subset(group={"Example"})) == 1
	assert len(d.subset(group={"Bad Wolf Corporation"})) == 4
	hits1 = d.search("Bad")
	hits2 = d.search("Bad", within={"title"})
	hits3 = d.search("bad", within={"title"}, ignore_case=True)
	assert len(hits1) == 5
	assert len(hits2) == 1
	assert len(hits3) == 1
	assert d["example0"] == d.get("example0")
	assert d.get("Bad Wolf") is None

def test_expdb_without_manifest():
	db = expdb(_testdb(), use_manifest=False)
	assert "example0" in db
	assert not db.manifest_exists()

def test_expdb_with_manifest():
	td = tempfile.TemporaryDirectory()
	root = shutil.copytree(_testdb(), os.path.join(td.name, "testdb"))
	db = expdb(root, use_manifest=True)
	assert "example0" in db
	assert db.manifest_exists()
	td.cleanup()

