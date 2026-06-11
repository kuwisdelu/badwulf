
import os
import json
import getpass
import tempfile

from badwulf.sync import syncer

from badwulf.util import touch
from badwulf.util import mktree
from badwulf.util import rmtree

def _testconfig():
	try:
		return os.path.join(os.path.dirname(__file__), 
			"testfiles", "badwulf-sites.json")
	except NameError:
		return os.path.join("..", "tests", 
			"testfiles", "badwulf-sites.json")

def test_syncer_init():
	sync = syncer.from_path(_testconfig())
	node = sync.node("origin")
	assert node.user == "bad-wolf"
	assert node.host == "time.vortex"
	assert node.proxy_user == "root"
	assert node.proxy_host == "login.dimension.time"
	assert sync.node("local").user == getpass.getuser()
	copy = syncer.from_dict(sync.to_dict())
	assert sync.to_dict() == copy.to_dict()

def test_syncer_push_pull():
	td = tempfile.TemporaryDirectory()
	sync = syncer.from_path(_testconfig())
	if sync.node("local").is_batch():
		pd1 = os.path.join(td.name, "testdir1")
		pd2 = os.path.join(td.name, "testdir2")
		tmp1 = os.path.join(pd1, "__badwulf_test")
		tmp2 = os.path.join(pd2, "__badwulf_test")
		mktree(pd1)
		mktree(pd2)
		touch(tmp1)
		sync.sites["self"].paths["default"] = pd1
		sync.sites["local"].paths["default"] = pd2
		sync.push("local", "__badwulf_test")
		assert os.path.exists(tmp1)
		assert os.path.exists(tmp2)
		os.remove(tmp1)
		assert not os.path.exists(tmp1)
		assert os.path.exists(tmp2)
		sync.pull("local", "__badwulf_test")
		assert os.path.exists(tmp1)
		assert os.path.exists(tmp2)
		rmtree(pd1, force=True)
		rmtree(pd2, force=True)
	td.cleanup()
