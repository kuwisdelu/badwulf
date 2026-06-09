
import os
import tomllib
import tempfile
import shutil

from badwulf.db import projmeta
from badwulf.db import projdata
from badwulf.db import projindex
from badwulf.db import projdb

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

def test_projdata_meta_search():
	p = ("public", "Example", "example0")
	proj = projdata.from_path(os.path.join(_testdb(), *p))
	assert proj.is_local()
	assert proj.size == proj.meta_size
	assert proj.meta.has_scope("public")
	assert proj.meta.has_group("Example")
	assert not proj.meta.has_scope("private")
	assert not proj.meta.has_group("Bad Wolf Corporation")
	s1 = proj.meta.search("bad wolf", ignore_case=True)
	s2 = proj.meta.search("Bad")
	s3 = proj.meta.search("Rose")
	s4 = proj.meta.search("example")
	s5 = proj.meta.search("example", within={"keywords"})
	assert s1.hits == {"contact": [{"name": "Bad Wolf"}]}
	assert "contact" in s2.hits
	assert s3 is None
	assert set(s4.hits.keys()) == {"name", "title", "keywords"}
	assert set(s5.hits.keys()) == {"keywords"}
	d = proj.to_dict()
	assert projdata.from_dict(d).to_dict() == proj.to_dict()

def test_projdata_move_copy_unlink():
	p = ("public", "Example", "example0")
	proj = projdata.from_path(os.path.join(_testdb(), *p))
	td = tempfile.TemporaryDirectory()
	dst_cp = os.path.join(td.name, "test-cp", *p)
	dst_mv = os.path.join(td.name, "test-mv", *p)
	dst_db = os.path.join(td.name, "test-db")
	proj2 = proj.copy(dst_cp)
	assert proj2.is_local()
	assert os.path.exists(proj.path)
	assert os.path.exists(proj2.path)
	assert proj2.path != proj.path
	assert proj2.meta == proj.meta
	assert proj2.meta_size == proj.meta_size
	assert proj2.is_misplaced_relative(dst_db)
	proj2.move(dst_mv)
	assert proj2.is_local()
	assert not os.path.exists(dst_cp)
	assert os.path.exists(proj2.path)
	assert proj2.path != proj.path
	assert proj2.meta == proj.meta
	assert proj2.meta_size == proj.meta_size
	assert proj2.is_misplaced_relative(dst_db)
	proj2.place_relative(dst_db)
	assert not proj2.is_misplaced_relative(dst_db)
	assert os.path.exists(proj2.path)
	proj2.unlink()
	assert not os.path.exists(proj2.path)
	assert os.path.exists(proj.path)
	td.cleanup()

def test_projindex():
	d = projindex.from_path(_testindex())
	assert "example0" in d
	assert isinstance(d["example0"], projdata)
	assert [k for k, v, in d.items()] == list(d.keys())
	assert [v for k, v, in d.items()] == list(d.values())
	assert d["example0"].is_local()
	sizes1 = [proj.size for proj in d.sorted_by("size")]
	sizes2 = [proj.size for proj in d.sorted_by("size", reverse=True)]
	assert sizes1 == sorted(sizes1)
	assert sizes2 == sorted(sizes2, reverse=True)
	mtimes1 = [proj.mtime for proj in d.sorted_by("mtime")]
	mtimes2 = [proj.mtime for proj in d.sorted_by("mtime", reverse=True)]
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

def test_projdb_without_manifest():
	db = projdb(_testdb(), use_manifest=False)
	assert "example0" in db
	assert not db.manifest_exists()

def test_projdb_with_manifest():
	td = tempfile.TemporaryDirectory()
	root = shutil.copytree(_testdb(), os.path.join(td.name, "testdb"))
	db = projdb(root, use_manifest=True)
	assert "example0" in db
	assert db.manifest_exists()
	td.cleanup()
