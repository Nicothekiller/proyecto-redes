from __future__ import annotations

from server.store.base import BaseStore
from server.store.memory import InMemoryStore
from server.store.sqlite import SQLiteStore

__all__ = ["BaseStore", "InMemoryStore", "SQLiteStore", "get_store", "set_store"]

_store: BaseStore = SQLiteStore()


def get_store() -> BaseStore:
    return _store


def set_store(store: BaseStore) -> None:
    global _store
    _store = store
