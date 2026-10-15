from __future__ import annotations

import uuid

import pytest

from server.store.base import BaseStore, DuplicatePubkeyError, UnknownNodeError
from server.store.db import engine, session_scope
from server.store.models import Node
from server.store.sqlite import SQLiteStore

A = uuid.UUID("11111111-1111-1111-1111-111111111111")
B = uuid.UUID("22222222-2222-2222-2222-222222222222")
C = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _delete(node_id: uuid.UUID) -> None:
    with session_scope() as session:
        node = session.get(Node, node_id)
        assert node is not None
        node.deleted = True


def test_register_allocates_sequential_ips(store: BaseStore) -> None:
    ip_a, peers_a = store.register(A, "pubA", "10.0.0.1:51820")
    ip_b, peers_b = store.register(B, "pubB", "10.0.0.2:51820")

    assert ip_a == "10.100.0.2"
    assert ip_b == "10.100.0.3"
    assert peers_a == []
    assert [(p.node_id, p.overlay_ip) for p in peers_b] == [(A, ip_a)]


def test_register_is_idempotent_for_same_node(store: BaseStore) -> None:
    ip_a, _ = store.register(A, "pubA", "10.0.0.1:51820")
    ip_again, _ = store.register(A, "pubA", "10.0.0.1:9999")

    assert ip_again == ip_a
    assert store.peers(A) == []

    store.register(B, "pubB", "10.0.0.2:51820")
    assert store.peers(B)[0].endpoint == "10.0.0.1:9999"


def test_register_rejects_duplicate_pubkey(store: BaseStore) -> None:
    store.register(A, "pubA", "10.0.0.1:51820")

    with pytest.raises(DuplicatePubkeyError):
        store.register(C, "pubA", "10.0.0.3:51820")


def test_register_rejects_pubkey_of_deleted_node(store: BaseStore) -> None:
    ip_a, _ = store.register(A, "pubA", "10.0.0.1:51820")
    _delete(A)

    with pytest.raises(DuplicatePubkeyError):
        store.register(C, "pubA", "10.0.0.3:51820")

    assert store.register(C, "pubC", "10.0.0.3:51820")[0] == "10.100.0.3"
    assert ip_a == "10.100.0.2"


def test_peers_excludes_self_and_deleted(store: BaseStore) -> None:
    store.register(A, "pubA", "10.0.0.1:51820")
    store.register(B, "pubB", "10.0.0.2:51820")
    store.register(C, "pubC", "10.0.0.3:51820")

    assert [p.node_id for p in store.peers(A)] == [B, C]

    _delete(B)
    assert [p.node_id for p in store.peers(A)] == [C]


def test_peers_unknown_node_raises(store: BaseStore) -> None:
    with pytest.raises(UnknownNodeError):
        store.peers(A)


def test_peers_deleted_requester_raises(store: BaseStore) -> None:
    store.register(A, "pubA", "10.0.0.1:51820")
    _delete(A)

    with pytest.raises(UnknownNodeError):
        store.peers(A)


def test_heartbeat_updates_endpoint_and_timestamp(store: BaseStore) -> None:
    store.register(A, "pubA", "10.0.0.1:51820")
    store.register(B, "pubB", "10.0.0.2:51820")

    with session_scope() as session:
        node_a = session.get(Node, A)
        assert node_a is not None
        before = node_a.last_heartbeat

    store.heartbeat(A, "10.0.0.1:60000")

    with session_scope() as session:
        node = session.get(Node, A)
        assert node is not None
        assert node.endpoint == "10.0.0.1:60000"
        assert node.last_heartbeat >= before
    assert store.peers(B)[0].endpoint == "10.0.0.1:60000"


def test_heartbeat_without_endpoint_keeps_it(store: BaseStore) -> None:
    store.register(A, "pubA", "10.0.0.1:51820")
    store.heartbeat(A)
    store.register(B, "pubB", "10.0.0.2:51820")

    assert store.peers(B)[0].endpoint == "10.0.0.1:51820"


def test_heartbeat_unknown_node_raises(store: BaseStore) -> None:
    with pytest.raises(UnknownNodeError):
        store.heartbeat(A, "10.0.0.1:51820")


def test_heartbeat_deleted_node_raises(store: BaseStore) -> None:
    store.register(A, "pubA", "10.0.0.1:51820")
    _delete(A)

    with pytest.raises(UnknownNodeError):
        store.heartbeat(A, "10.0.0.1:51820")


def test_revive_deleted_node_keeps_ip(store: BaseStore) -> None:
    ip_b, _ = store.register(B, "pubB", "10.0.0.2:51820")
    store.register(A, "pubA", "10.0.0.1:51820")
    _delete(B)
    assert [p.node_id for p in store.peers(A)] == []

    revived_ip, _ = store.register(B, "pubB", "10.0.0.2:51820")

    assert revived_ip == ip_b
    assert [p.node_id for p in store.peers(A)] == [B]


def test_restart_keeps_ips(store: BaseStore) -> None:
    ip_a, _ = store.register(A, "pubA", "10.0.0.1:51820")
    ip_b, _ = store.register(B, "pubB", "10.0.0.2:51820")

    engine.dispose()
    restarted = SQLiteStore()

    ip_a_again, _ = restarted.register(A, "pubA", "10.0.0.1:51820")
    ip_b_again, _ = restarted.register(B, "pubB", "10.0.0.2:51820")

    assert (ip_a_again, ip_b_again) == (ip_a, ip_b)
    assert [p.node_id for p in restarted.peers(A)] == [B]
