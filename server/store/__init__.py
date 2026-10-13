from __future__ import annotations

from server.store.base import BaseStore
from server.store.memory import InMemoryStore

_store: BaseStore = InMemoryStore()


def get_store() -> BaseStore:
    return _store


def set_store(store: BaseStore) -> None:
    global _store
    _store = store
