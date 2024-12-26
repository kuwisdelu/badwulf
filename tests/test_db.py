
import os
import sys
if sys.version_info >= (3, 11):
	import tomllib
else:
	import tomli as tomllib

import pytest

from badwulf.db import *

try:
	dbpath = os.path.dirname(__file__)
	dbpath = os.path.join(dbpath, "testdb")
except:
	dbpath = os.path.join("tests", "testdb")

def test_toml_parse():
	path = os.path.join(dbpath, "manifest.toml")
	with open(path, "rb") as file:
		manifest = tomllib.load(file)
	assert isinstance(manifest, dict)

@pytest.fixture
def database():
	return expdb("bad-wolf", dbpath, None, autoconnect=False)

def test_db_open(database):
	with database as db:
		assert db.isopen()

def test_db_get(database):
	with database as db:
		assert db.get("Dataset-id") == db["Dataset-id"]

def test_db_ls(database):
	with database as db:
		assert "Dataset-id" in db.ls()

def test_db_ls_cache(database):
	with database as db:
		assert len(db.ls_cache()) == 0

def test_db_search(database):
	with database as db:
		assert len(db.search("test")) == 0
		assert len(db.search("computational")) == 1
		assert len(db.search("protocol")) == 1

def test_db_search_cache(database):
	with database as db:
		assert len(db.search_cache("test")) == 0
		assert len(db.search_cache("computational")) == 0
		assert len(db.search_cache("protocol")) == 0

def test_db_status(database):
	with database as db:
		synced, remoteonly, localonly = db.status()
		assert len(synced) == 0
		assert len(remoteonly) == 1
		assert len(localonly) == 0
