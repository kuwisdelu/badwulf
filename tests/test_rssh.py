
from badwulf import rssh

def test_rssh_without_gateway():
	con = rssh("bad-wolf", "vortex")
	assert con.username == "bad-wolf"
	assert con.destination == "vortex"
	assert con.hostname == "vortex"
	assert con.server is None
	assert con.server_username == "bad-wolf"
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
