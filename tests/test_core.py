import os
import shutil
import tomllib
import getpass
import tempfile

from badwulf.core import profile
from badwulf.core import profiles
from badwulf.core import dbsyncer
from badwulf.util import touch
from badwulf.util import mkpath
from badwulf.util import mktree
from badwulf.util import rmtree

def _testsites():
	try:
		return os.path.join(os.path.dirname(__file__), 
			"testfiles", "badwulf-sites.json")
	except NameError:
		return os.path.join("..", "tests", 
			"testfiles", "badwulf-sites.json")

def test_profile():
	pf = profile(
		hosts={"0": "node0"},
		paths={"a": "/projects/a"})
	pf.set_default_host("head")
	pf.set_default_path("/home")
	assert pf.normalize_host_alias("0") == "0"
	assert pf.normalize_path_alias("a") == "a"
	assert pf.normalize_host_alias(None) == "default"
	assert pf.normalize_path_alias(None) == "default"
	assert pf.get_host("0") == pf.hosts["0"]
	assert pf.get_path("a") == pf.paths["a"]
	assert pf.get_host(None) == pf.hosts["default"]
	assert pf.get_path(None) == pf.paths["default"]
	assert pf.get_host_alias_for("node0") == "0"
	assert pf.get_host_alias_for("NODE0") == "0"
	assert pf.get_path_alias_for("/projects/a") == "a"
	assert pf.get_path_alias_for("/projects/a/b/c", parents=True) == "a"

def test_profiles():
	sts = profiles.from_path(_testsites())
	assert "local" in sts
	test = profile()
	assert sts.get("test") is None
	sts["test"] = test
	assert sts["test"] == test
	del sts["test"]
	assert "test" not in sts
	copy = profiles.from_dict(sts.to_dict())
	assert sts.to_dict() == copy.to_dict()

def test_dbsyncer_sites():
	dbs = dbsyncer.from_path(_testsites())
	assert db.local_name == "local"
	assert dbs.local == dbs.sites["local"]
	origin = dbs.remote("origin")
	assert origin.user == "bad-wolf"
	assert origin.host == "time.vortex"
	assert origin.proxy_user == "root"
	assert origin.proxy_host == "login.dimension.time"
	other = dbs.remote("other")
	assert other.user == getpass.getuser()
	assert other.host == "localhost"

def test_dbsyncer_proj_sync():
	td = tempfile.TemporaryDirectory()
	dbs = dbsyncer.from_path(_testsites())
	pd1 = os.path.join(td.name, "testdir1")
	pd2 = os.path.join(td.name, "testdir2")
	os.environ["BADWULF_TESTDIR1"] = pd1
	os.environ["BADWULF_TESTDIR2"] = pd2
	mktree(pd1)
	mktree(pd2)
	db = dbs.get_db()
	proj = db.create(
		name="test0",
		scope="private",
		group="scratch")
	assert os.path.exists(proj.meta_path)
	with open(proj.meta_path, "rb") as f:
		d = tomllib.load(f)
	assert d == proj.meta.to_dict()
	td.cleanup()
