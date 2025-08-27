
import os
import tempfile
import pytest

from badwulf import rssh
from badwulf.tools import *

def test_rssh_without_gateway():
	con = rssh("bad-wolf", "vortex")
	assert con.username == "bad-wolf"
	assert con.destination == "vortex"
	assert con.hostname == "vortex"
	assert con.server is None
	assert con.server_username is None
	assert not con.isopen()

def test_rssh_with_gateway():
	con = rssh("bad-wolf", "vortex",
		server="login.dimension.time",
		server_username="root",
		autoconnect=False)
	assert con.username == "bad-wolf"
	assert con.destination == "vortex"
	assert con.hostname == "localhost"
	assert con.server == "login.dimension.time"
	assert con.server_username == "root"
	assert not con.isopen()

def test_rssh_upload_download_file():
	con = rssh(os.getenv("USER"), "localhost")
	if con.isbatch():
		tmpdir = tempfile.gettempdir()
		tmp1 = os.path.join(tmpdir, "__badwulf_testfile__")
		tmp2 = os.path.join(tmpdir, "__badwulf_testfile_download__")
		tmp3 = os.path.join(tmpdir, "__badwulf_testfile_upload__")
		file_create(tmp1)
		assert os.path.exists(tmp1)
		con.download(tmp1, tmp2)
		assert os.path.exists(tmp2)
		con.upload(tmp2, tmp3)
		assert os.path.exists(tmp3)
		file_remove(tmp1)
		file_remove(tmp2)
		file_remove(tmp3)
