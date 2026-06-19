
import os
import tomllib
import tempfile
import shutil

from badwulf.db import projmeta
from badwulf.db import projdata
from badwulf.db import projdb

def _testmanifest():
	try:
		return os.path.join(os.path.dirname(__file__), 
			"testfiles", "manifest.json")
	except NameError:
		return os.path.join("..", "tests", 
			"testfiles", "manifest.json")

def _testdb():
	try:
		return os.path.join(os.path.dirname(__file__), 
			"testdb")
	except NameError:
		return os.path.join("..", "tests", 
			"testdb")

def test_projdata_meta_search():
	p = ("public", "example", "example0")
	proj = projdata.from_path(os.path.join(_testdb(), *p))
	assert proj.is_local()
	assert proj.size == proj.meta_size
	assert proj.meta.has_scope("public")
	assert proj.meta.has_group("example")
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
	p = ("public", "example", "example0")
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

def test_projdb_manifest_only():
	db = projdb.from_manifest(_testmanifest())
	assert "example0" in db
	assert isinstance(db["example0"], projdata)
	assert [k for k, v, in db.items()] == list(db.keys())
	assert [v for k, v, in db.items()] == list(db.values())
	assert db["example0"].is_local()
	sizes1 = [proj.size for proj in db.sorted_by("size").projects]
	sizes2 = [proj.size for proj in db.sorted_by("size", reverse=True).projects]
	assert sizes1 == sorted(sizes1)
	assert sizes2 == sorted(sizes2, reverse=True)
	mtimes1 = [proj.mtime for proj in db.sorted_by("mtime").projects]
	mtimes2 = [proj.mtime for proj in db.sorted_by("mtime", reverse=True).projects]
	assert mtimes1 == sorted(mtimes1)
	assert mtimes2 == sorted(mtimes2, reverse=True)
	assert len(db.subset({"data0", "data1"})) == 2
	assert len(db.subset(scope={"public"})) == 1
	assert len(db.subset(scope={"private"})) == 4
	assert len(db.subset({"data0"}, scope={"public"})) == 0
	assert len(db.subset({"data0"}, scope={"private"})) == 1
	assert len(db.subset(group={"Example"})) == 1
	assert len(db.subset(group={"Bad Wolf Corporation"})) == 4
	hits1 = db.search("Bad")
	hits2 = db.search("Bad", within={"title"})
	hits3 = db.search("bad", within={"title"}, ignore_case=True)
	assert len(hits1) == 5
	assert len(hits2) == 1
	assert len(hits3) == 1
	assert db["example0"] == db.get("example0")
	assert db.get("Bad Wolf") is None

def test_projdb_with_root():
	td = tempfile.TemporaryDirectory()
	root = shutil.copytree(_testdb(), os.path.join(td.name, "testdb"))
	db = projdb.from_root(root)
	assert "example0" in db
	assert not db.manifest_exists()
	db.refresh()
	assert db.manifest_exists()
	size1 = os.stat(db.manifest).st_size
	proj = projdata("/dev/null")
	proj.meta = projmeta(name="NULL", scope="private", group="scratch")
	db["null"] = proj
	assert "null" in db
	assert db["null"] == proj
	del db["null"]
	assert "null" not in db
	del db["example0"]
	assert "example0" not in db
	db.save()
	size2 = os.stat(db.manifest).st_size
	assert size2 < size1
	db.rebuild()
	size3 = os.stat(db.manifest).st_size
	assert size3 > size2
	assert "example0" in db
	db.refresh()
	size4 = os.stat(db.manifest).st_size
	assert size4 == size3
	assert "example0" in db
	td.cleanup()
