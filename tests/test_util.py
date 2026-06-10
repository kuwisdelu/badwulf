
import os
import platform
import tempfile

from badwulf.util import to_bytes
from badwulf.util import format_bytes
from badwulf.util import quote
from badwulf.util import touch
from badwulf.util import mkpath
from badwulf.util import mktree
from badwulf.util import rmtree
from badwulf.util import tree_find
from badwulf.util import tree_stat
from badwulf.util import findport
from badwulf.util import checkport
from badwulf.util import grep
from badwulf.util import prune

def test_to_bytes():
	assert to_bytes(1) == 1
	assert to_bytes(1, "KB") == 1_000
	assert to_bytes(1, "MB") == 1_000_000
	assert to_bytes(1, "GB") == 1_000_000_000

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

def test_mkpath_mktree_etc():
	td = tempfile.TemporaryDirectory()
	pd = mkpath(td.name, "__badwulf_testdir__")
	assert not os.path.exists(pd)
	mktree(pd)
	assert os.path.exists(pd)
	assert os.path.isdir(pd)
	tmp = mkpath(pd, "__badwulf_testfile__")
	touch(tmp)
	assert os.path.exists(tmp)
	assert tmp in tree_find(pd, "testfile")
	with open(tmp, "a") as f:
		f.write("I am the Bad Wolf.")
	st = tree_stat(pd)
	assert st["size"] == 18
	rmtree(pd, force=True)
	assert not os.path.exists(tmp)
	assert not os.path.exists(pd)	
	td.cleanup()

def test_findport_checkport():
	p = findport(attempts=50)
	assert checkport(p) != 0

def test_grep():
	sl = [
		"I am the Bad Wolf.",
		"I create myself.",
		"I take the words, I scatter them in time and space.",
		"A message to lead myself here."]
	d = {
		"First": "I am the Bad Wolf.",
		"Final": sl}
	q1 = grep("bad wolf", sl[0], ignore_case=True)
	assert q1 is not None
	assert q1.span() == (9, 17)
	q2 = grep("bad wolf", sl[0], ignore_case=True, context_width=8)
	assert q2 == "Bad Wolf"
	q3 = grep("bad wolf", sl[0], ignore_case=True, context_width=20)
	assert q3 == sl[0]
	q4 = grep("bad wolf", sl[0], ignore_case=False)
	assert q4 is None
	qs1 = grep("bad wolf", sl, ignore_case=True, context_width=0)
	assert qs1 == ["Bad Wolf", None, None, None]
	qs2 = grep("bad wolf", d, ignore_case=True, context_width=0)
	assert qs2["First"] == "Bad Wolf"
	assert qs2["Final"] == ["Bad Wolf", None, None, None]

def test_prune():
	l = [1, 2, None]
	assert prune(l) == [1, 2]
	d = {"a": 1, "b": 2, "c": None}
	assert prune(d) == {"a": 1, "b": 2}
	x1 = [l, d]
	assert prune(x1) == [[1, 2], {"a": 1, "b": 2}]
	x2 = [{"b": None}]
	assert prune(x2) == []
	x3 = {"a": {"b": None}}
	assert prune(x3) == {}
