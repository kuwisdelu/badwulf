
import os
import tempfile
import pytest

from badwulf.tools import *

def test_to_bytes():
	assert to_bytes(1) == 1
	assert to_bytes(1, "KB") == 1_000
	assert to_bytes(1, "MB") == 1_000_000

def test_format_bytes():
	assert format_bytes(1) == "1 byte"
	assert format_bytes(100) == "100 bytes"
	assert format_bytes(1_000) == "1.0 KB"
	assert format_bytes(1_000_000) == "1.0 MB"

def test_fix_path_err():
	tmpdir = tempfile.gettempdir()
	tmp = os.path.join(tmpdir, "__badwulf_testfile__")
	if os.path.exists(tmp):
		os.remove(tmp)
	with pytest.raises(FileNotFoundError) as err:
		fix_path(tmp)
	assert "path does not exist" in str(err.value)

def test_file_create_remove():
	tmpdir = tempfile.gettempdir()
	tmp = os.path.join(tmpdir, "__badwulf_testfile__")
	if os.path.exists(tmp):
		os.remove(tmp)
	file_create(tmp)
	assert os.path.exists(tmp)
	assert os.path.basename(tmp) in ls(tmpdir)
	file_remove(tmp)
	assert not os.path.exists(tmp)

def test_findport():
	p = findport()
	assert checkport(p) != 0

@pytest.fixture
def string_list():
	return [
		"I am the Bad Wolf.",
		"I create myself.",
		"I take the words, I scatter them in time and space.",
		"A message to lead myself here."]

def test_grep1(string_list):
	q = grep1("bad wolf", string_list[0])
	assert q is not None
	assert q.span() == (9, 17)

def test_grep1_context(string_list):
	q1 = grep1("bad wolf", string_list[0], context_width=8)
	assert q1 == "Bad Wolf"
	q2 = grep1("bad wolf", string_list[0], context_width=20)
	assert q2 == string_list[0]

def test_grepl(string_list):
	qs = grepl("bad wolf", string_list)
	assert qs == [True, False, False, False]
