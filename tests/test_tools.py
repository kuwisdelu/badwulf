
import os
import platform
import tempfile
import pytest

from badwulf.tools import *

def test_is_known_host():
	host = platform.node().replace(".local", "")
	assert is_known_host([host])

def test_to_bytes():
	assert to_bytes(1) == 1
	assert to_bytes(1, "KB") == 1_000
	assert to_bytes(1, "MB") == 1_000_000

def test_format_bytes():
	assert format_bytes(1) == "1 byte"
	assert format_bytes(1_000, "KB") == "1.0 KB"
	assert format_bytes(1_100, "KB") == "1.1 KB"
	assert format_bytes(1_000_000, "auto") == "1.0 MB"
	assert format_bytes(1_100_000, "auto") == "1.1 MB"
	assert format_bytes(1_000_000, "KB") == "1000.0 KB"
	assert format_bytes(1_100_000, "KB") == "1100.0 KB"

def test_quote():
	assert quote("Bad Wolf") == '"Bad Wolf"'
	assert quote("Bad Wolf", "'") == "'Bad Wolf'"
	assert quote("Bad Wolf", "|") == "|Bad Wolf|"

def test_fix_path_err():
	tmpdir = tempfile.gettempdir()
	tmp = os.path.join(tmpdir, "__badwulf_testfile__")
	if os.path.exists(tmp):
		os.remove(tmp)
	with pytest.raises(FileNotFoundError) as err:
		fix_path(tmp)
	assert "path does not exist" in str(err.value)

def test_file_create_remove_ls():
	tmpdir = tempfile.gettempdir()
	tmp = os.path.join(tmpdir, "__badwulf_testfile__")
	file_create(tmp)
	assert os.path.exists(tmp)
	assert os.path.basename(tmp) in ls(tmpdir)
	file_remove(tmp)
	assert not os.path.exists(tmp)
	assert not os.path.basename(tmp) in ls(tmpdir)

def test_dir_create_remove_stat():
	tmpdir = tempfile.gettempdir()
	dtmp = os.path.join(tmpdir, "__badwulf_testdir__")
	tmp = os.path.join(dtmp, "__badwulf_testfile__")
	dir_create(dtmp)
	assert os.path.exists(dtmp)
	assert os.path.isdir(dtmp)
	with open(tmp, "a") as f:
		f.write("I am the Bad Wolf.")
	st = dir_stat(dtmp)
	assert st["size"] == 18
	assert st["size"] == dir_size(tmpdir)
	dir_remove(dtmp, force=True)
	assert not os.path.exists(dtmp)

def test_findport_checkport():
	p = findport(attempts=50)
	assert checkport(p) != 0

def test_grep():
	sl = [
		"I am the Bad Wolf.",
		"I create myself.",
		"I take the words, I scatter them in time and space.",
		"A message to lead myself here."]
	sd = {
		"First": "I am the Bad Wolf.",
		"Final": sl}
	q1 = grep1("bad wolf", sl[0])
	assert q1 is not None
	assert q1.span() == (9, 17)
	q2 = grep1("bad wolf", sl[0], context_width=8)
	assert q2 == "Bad Wolf"
	q3 = grep1("bad wolf", sl[0], context_width=20)
	assert q3 == sl[0]
	q4 = grep1("bad wolf", sl[0], ignore_case=False)
	assert q4 is None
	qs1 = grep("bad wolf", sl, context_width=0)
	assert qs1 == ["Bad Wolf", None, None, None]
	qs2 = grep("bad wolf", sd, context_width=0)
	assert qs2["First"] == "Bad Wolf"
	assert qs2["Final"] == ["Bad Wolf", None, None, None]

def test_prune_none():
	l = [1, 2, None]
	assert prune_none(l) == [1, 2]
	d = {"a": 1, "b": 2, "c": None}
	assert prune_none(d) == {"a": 1, "b": 2}
	x = [l, d]
	assert prune_none(x)[0] == [1, 2]
	assert prune_none(x)[1] == {"a": 1, "b": 2}

def test_maybe_template():
	assert maybe_template("{}")
	assert maybe_template("{prefix}/{user}")
	assert maybe_template("path/with {space}/x")
	assert not maybe_template("/time/vortex.txt")
	assert not maybe_template("weird}_path")
	assert not maybe_template("escaped {{braces}}")
