from __future__ import annotations

import uuid

import pytest

from server.store.base import BaseStore, PeerReportRecord, UnknownNodeError

A = uuid.UUID("11111111-1111-1111-1111-111111111111")
B = uuid.UUID("22222222-2222-2222-2222-222222222222")
C = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _register(store: BaseStore, node_id: uuid.UUID, pubkey: str) -> str:
    overlay_ip, _ = store.register(node_id, pubkey, "10.0.0.1:51820")
    return overlay_ip


def _report(
    peer_id: uuid.UUID,
    *,
    last_handshake: int = 0,
    rx_bytes: int = 0,
    tx_bytes: int = 0,
    endpoint: str | None = None,
    probe_ok: bool | None = None,
    probe_rtt_ms: float | None = None,
) -> PeerReportRecord:
    return PeerReportRecord(
        peer_id=peer_id,
        last_handshake=last_handshake,
        rx_bytes=rx_bytes,
        tx_bytes=tx_bytes,
        endpoint=endpoint,
        probe_ok=probe_ok,
        probe_rtt_ms=probe_rtt_ms,
    )


def test_heartbeat_stores_directed_pair(store: BaseStore) -> None:
    _register(store, A, "pubA")
    _register(store, B, "pubB")

    store.heartbeat(
        A,
        peers=[PeerReportRecord(peer_id=B, last_handshake=100, rx_bytes=10, tx_bytes=20)],
    )

    pairs = store.pairs()
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.reporter == A
    assert pair.peer == B
    assert pair.reporter_overlay_ip == "10.100.0.2"
    assert pair.peer_overlay_ip == "10.100.0.3"
    assert pair.last_handshake == 100
    assert pair.rx_bytes == 10
    assert pair.tx_bytes == 20
    assert pair.probe_ok is None
    assert pair.probe_ran_at is None


def test_heartbeat_upserts_same_pair(store: BaseStore) -> None:
    _register(store, A, "pubA")
    _register(store, B, "pubB")

    store.heartbeat(A, peers=[_report(B, last_handshake=100, rx_bytes=10, tx_bytes=20)])
    store.heartbeat(A, peers=[_report(B, last_handshake=200, rx_bytes=50, tx_bytes=60)])

    pairs = store.pairs()
    assert len(pairs) == 1
    assert pairs[0].last_handshake == 200
    assert pairs[0].rx_bytes == 50
    assert pairs[0].tx_bytes == 60


def test_heartbeat_records_probe(store: BaseStore) -> None:
    _register(store, A, "pubA")
    _register(store, B, "pubB")

    store.heartbeat(A, peers=[_report(B, probe_ok=True, probe_rtt_ms=1.5)])

    pair = store.pairs()[0]
    assert pair.probe_ok is True
    assert pair.probe_rtt_ms == 1.5
    assert pair.probe_ran_at is not None


def test_heartbeat_failed_probe_keeps_none_rtt(store: BaseStore) -> None:
    _register(store, A, "pubA")
    _register(store, B, "pubB")

    store.heartbeat(A, peers=[_report(B, probe_ok=False)])

    pair = store.pairs()[0]
    assert pair.probe_ok is False
    assert pair.probe_rtt_ms is None


def test_heartbeat_unknown_peer_raises(store: BaseStore) -> None:
    _register(store, A, "pubA")

    with pytest.raises(UnknownNodeError):
        store.heartbeat(A, peers=[_report(B)])


def test_pairs_are_directed_and_sorted(store: BaseStore) -> None:
    _register(store, A, "pubA")
    _register(store, B, "pubB")
    _register(store, C, "pubC")

    store.heartbeat(B, peers=[_report(A)])
    store.heartbeat(A, peers=[_report(B), _report(C)])

    assert [(p.reporter_overlay_ip, p.peer_overlay_ip) for p in store.pairs()] == [
        ("10.100.0.2", "10.100.0.3"),
        ("10.100.0.2", "10.100.0.4"),
        ("10.100.0.3", "10.100.0.2"),
    ]


def test_delete_cascades_peer_status(store: BaseStore) -> None:
    _register(store, A, "pubA")
    _register(store, B, "pubB")
    store.heartbeat(A, peers=[_report(B)])

    store.delete(B)

    assert store.pairs() == []


def test_heartbeat_without_peers_leaves_pairs_untouched(store: BaseStore) -> None:
    _register(store, A, "pubA")
    _register(store, B, "pubB")
    store.heartbeat(A, peers=[_report(B, last_handshake=42)])

    store.heartbeat(A, endpoint="10.0.0.9:51820")

    pairs = store.pairs()
    assert len(pairs) == 1
    assert pairs[0].last_handshake == 42
