
import os
import pytest

from badwulf import expdb

@pytest.fixture
def database():
	try:
		dbpath = os.path.dirname(__file__)
		dbpath = os.path.join(dbpath, "testdb")
	except:
		dbpath = os.path.join("tests", "testdb")
	return expdb("bad-wolf", dbpath, None, autoconnect=False)

def test_db_open(database):
	with database as db:
		assert db.isopen()

def test_db_get(database):
	with database as db:
		assert db.get("Test-data-01") == db["Test-data-01"]

def test_db_ls(database):
	with database as db:
		assert "Test-data-01" in db.ls()

def test_db_ls_cache(database):
	with database as db:
		assert len(db.ls_cache()) == 0

def test_db_search(database):
	with database as db:
		assert len(db.search("bad wolf")) == 1
		assert len(db.search("myself")) == 2
		assert len(db.search("secret")) == 0

def test_db_search_cache(database):
	with database as db:
		assert len(db.search_cache("bad wolf")) == 0
		assert len(db.search_cache("myself")) == 0
		assert len(db.search_cache("secret")) == 0

def test_db_describe(database):
	with database as db:
		assert db["Test-data-01"].describe() is not None
		assert db["Test-data-02"].describe() is not None
		assert db["Test-data-03"].describe() is not None
		assert db["Test-data-04"].describe() is not None

def test_db_status(database):
	with database as db:
		synced, remoteonly, localonly = db.status()
		assert len(synced) == 0
		assert len(remoteonly) == 4
		assert len(localonly) == 0
