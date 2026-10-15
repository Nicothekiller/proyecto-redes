from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from server.store.base import BaseStore

_TMPDIR = tempfile.mkdtemp(prefix="wg-coord-tests-")
os.environ["API_KEY"] = "testkey"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test.db"


@pytest.fixture()
def store() -> Iterator[BaseStore]:
    from server.store.db import engine
    from server.store.models import Base
    from server.store.sqlite import SQLiteStore

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield SQLiteStore()
