import os
import shutil
import tomllib
import getpass
import tempfile

from badwulf.core import LOCAL_SITE
from badwulf.core import DEFAULT_HOST
from badwulf.core import DEFAULT_PREFIX
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

def _testdb():
	try:
		return os.path.join(os.path.dirname(__file__), 
			"testdb")
	except NameError:
		return os.path.join("..", "tests", 
			"testdb")

def test_profile():
	p = profile(
		hosts={"0": "node0"},
		paths={"a": "/projects/a"})
	assert p.alias_of_host("node0") == "0"
	assert p.alias_of_host("NODE0") == "0"
	assert p.alias_of_path("/projects/a") == "a"
	assert p.alias_of_path("/projects/a/b/c", parents=True) == "a"

def test_profiles():
	sts = profiles.from_path(_testsites())
	assert LOCAL_SITE in sts
	test = profile()
	assert sts.get("test") is None
	sts["test"] = test
	assert sts["test"] == test
	del sts["test"]
	assert "test" not in sts
	copy = profiles.from_dict(sts.to_dict())
	assert sts.to_dict() == copy.to_dict()

def test_dbsyncer_sites():
	dbs = dbsyncer(_testsites())
	assert dbs.sites[LOCAL_SITE] == dbs.local
	origin = dbs.bridge("origin")
	assert origin.user == "bad-wolf"
	assert origin.host == "time.vortex"
	assert origin.proxy_user == "root"
	assert origin.proxy_host == "login.dimension.time"
	other = dbs.bridge("other")
	assert other.user == getpass.getuser()
	assert other.host == "localhost"

def test_dbsyncer_push_pull():
	td = tempfile.TemporaryDirectory()
	dbs = dbsyncer(_testsites())
	pd1 = os.path.join(td.name, "testdir1")
	pd2 = os.path.join(td.name, "testdir2")
	os.environ["BADWULF_TESTDIR1"] = pd1
	os.environ["BADWULF_TESTDIR2"] = pd2
	shutil.copytree(_testdb(), pd1)
	db = dbs.get(prefix=DEFAULT_PREFIX)
	db.load()
	assert "example0" in db
	td.cleanup()
