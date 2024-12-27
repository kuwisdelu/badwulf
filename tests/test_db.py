
import os
import pytest

from badwulf.db import *

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
		assert db.get("Dataset-ID") == db["Dataset-ID"]

def test_db_ls(database):
	with database as db:
		assert "Dataset-ID" in db.ls()

def test_db_ls_cache(database):
	with database as db:
		assert len(db.ls_cache()) == 0

def test_db_search(database):
	with database as db:
		assert len(db.search("test")) == 0
		assert len(db.search("research")) == 1

def test_db_search_cache(database):
	with database as db:
		assert len(db.search_cache("test")) == 0
		assert len(db.search_cache("research")) == 0

def test_db_status(database):
	with database as db:
		synced, remoteonly, localonly = db.status()
		assert len(synced) == 0
		assert len(remoteonly) == 1
		assert len(localonly) == 0

def test_db_close(database):
	database.close()
	assert not database.isopen()
