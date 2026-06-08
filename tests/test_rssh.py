
import os
import tempfile

from badwulf import rssh

from badwulf.tools import file_create
from badwulf.tools import file_remove
from badwulf.tools import dir_create
from badwulf.tools import dir_remove

def test_rssh_init_without_proxy():
	con = rssh(
		user="bad-wolf", 
		host="vortex")
	assert con.destination == "bad-wolf@vortex"
	assert con.proxy_destination is None
	assert not con.has_proxy_jump()
	assert not con.is_open()
	assert con.rsh == ["ssh"]
	assert con.proxy_port is None

def test_rssh_init_with_proxy():
	con = rssh(
		user="bad-wolf", 
		host="vortex",
		proxy_user="root",
		proxy_host="login.dimension.time")
	assert con.destination == "bad-wolf@vortex"
	assert con.proxy_destination == "root@login.dimension.time"
	assert con.has_proxy_jump()
	assert not con.is_open()
	assert con.rsh == ["ssh", "-o", "ProxyJump=root@login.dimension.time"]
	assert con.proxy_port is not None

def test_rssh_push_pull_file():
	con = rssh("$USER", "localhost")
	td = tempfile.TemporaryDirectory()
	if con.is_batch():
		tmp1 = os.path.join(td.name, "__badwulf_test")
		tmp2 = os.path.join(td.name, "__badwulf_test_push")
		tmp3 = os.path.join(td.name, "__badwulf_test_pull")
		file_create(tmp1)
		assert os.path.exists(tmp1)
		assert not os.path.exists(tmp2)
		assert not os.path.exists(tmp3)
		con.push(tmp1, tmp2)
		assert os.path.exists(tmp1)
		assert os.path.exists(tmp2)
		assert not os.path.exists(tmp3)
		con.pull(tmp2, tmp3)
		assert os.path.exists(tmp1)
		assert os.path.exists(tmp2)
		assert os.path.exists(tmp3)
	td.cleanup()

def test_rssh_push_pull_dir():
	con = rssh("$USER", "localhost")
	td = tempfile.TemporaryDirectory()
	if con.is_batch():
		pd1 = os.path.join(td.name, "testdir1")
		pd2 = os.path.join(td.name, "testdir2")
		tmp1a = os.path.join(pd1, "__badwulf_test-a")
		tmp1b = os.path.join(pd1, "__badwulf_test-b")
		tmp2a = os.path.join(pd2, "__badwulf_test-a")
		tmp2b = os.path.join(pd2, "__badwulf_test-b")
		dir_create(pd1)
		file_create(tmp1a)
		file_create(tmp1b)
		assert os.path.exists(tmp1a)
		assert os.path.exists(tmp1b)
		if pd1[-1] != "/":
			pd1 += "/"
		if pd2[-1] != "/":
			pd2 += "/"
		con.push(pd1, pd2)
		assert os.path.exists(tmp2a)
		assert os.path.exists(tmp2b)
		dir_remove(pd1, force=True)
		assert not os.path.exists(pd1)
		con.pull(pd2, pd1)
		assert os.path.exists(tmp1a)
		assert os.path.exists(tmp1b)
	td.cleanup()
