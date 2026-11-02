from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

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


@pytest.fixture()
def client(store: BaseStore) -> Iterator[TestClient]:
    from fastapi.testclient import TestClient

    from server.main import app
    from server.store import set_store

    set_store(store)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def live_server(store: BaseStore) -> Iterator[str]:
    import uvicorn

    from server.main import app
    from server.store import set_store

    set_store(store)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(5)
    sock.close()
