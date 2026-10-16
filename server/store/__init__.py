from __future__ import annotations

from server.store.base import BaseStore
from server.store.sqlite import SQLiteStore

__all__ = ["BaseStore", "SQLiteStore", "get_store", "set_store"]

_store: BaseStore = SQLiteStore()


def get_store() -> BaseStore:
    return _store


def set_store(store: BaseStore) -> None:
    global _store
    _store = store
