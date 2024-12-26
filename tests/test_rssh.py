
from badwulf.rssh import *

def test_rssh_without_gateway():
	con = rssh("the-doctor", "tardis")
	assert con.username == "the-doctor"
	assert con.destination == "tardis"
	assert con.hostname == "tardis"
	assert con.server is None
	assert con.server_username == "the-doctor"
	assert not con.isopen()

def test_rssh_with_gateway():
	con = rssh("rose-tyler", "tardis",
		server="time-vortex",
		server_username="bad-wolf",
		autoconnect=False)
	assert con.username == "rose-tyler"
	assert con.destination == "tardis"
	assert con.hostname == "localhost"
	assert con.server == "time-vortex"
	assert con.server_username == "bad-wolf"
	assert not con.isopen()
