import importlib
import os
import runpy
import secrets
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def seeded_data(tmp_path_factory):
    # Run the destructive seed only from a temporary copy.
    directory = tmp_path_factory.mktemp("meridian-seed")
    seed = directory / "seed.py"
    seed.write_bytes((PROJECT / "seed.py").read_bytes())
    runpy.run_path(str(seed))
    return directory


@pytest.fixture
def client(seeded_data, tmp_path, monkeypatch):
    monkeypatch.setenv("MERIDIAN_SECRET_KEY", secrets.token_hex(32))
    monkeypatch.setenv("MERIDIAN_HTTPS", "0")
    meridian = importlib.import_module("app")
    database = tmp_path / "expenses.db"
    database.write_bytes((seeded_data / "expenses.db").read_bytes())
    monkeypatch.setattr(meridian, "DB", os.fspath(database))
    monkeypatch.setattr(meridian, "RECEIPTS", os.fspath(seeded_data / "receipts"))
    monkeypatch.setitem(meridian.app.config, "TESTING", True)
    with meridian.app.test_client() as browser:
        yield browser
