from __future__ import annotations

import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

import pytest
import requests

from client import probe, stats, wg
from client.api import Peer, ServerClient
from client.loop import Agent, PeerDelta, diff_peers
from client.state import NodeState
from server.store.base import BaseStore

A = uuid.UUID("11111111-1111-1111-1111-111111111111")
B = uuid.UUID("22222222-2222-2222-2222-222222222222")
C = uuid.UUID("33333333-3333-3333-3333-333333333333")

PUB_B = "B" * 43 + "="
PUB_B2 = "D" * 43 + "="
PUB_C = "C" * 43 + "="


def _peer(pubkey: str = PUB_B, endpoint: str = "10.0.0.2:51820") -> Peer:
    return Peer(node_id=B, overlay_ip="10.100.0.3", pubkey=pubkey, endpoint=endpoint)


@pytest.fixture()
def wg_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(wg.subprocess, "run", run)
    monkeypatch.setattr(probe, "probe_all", lambda ips: {})
    monkeypatch.setattr(stats, "collect", lambda iface: {})
    return calls


def _agent(live_server: str, store: BaseStore, tmp_path: Path) -> Agent:
    overlay_ip, peers = store.register(A, "pubA", "127.0.0.1:51820")
    return Agent(
        ServerClient(live_server, "testkey"),
        live_server,
        NodeState(node_id=A, overlay_ip=overlay_ip),
        "privA",
        tmp_path / "wg0.conf",
        [Peer(p.node_id, p.overlay_ip, p.pubkey, p.endpoint) for p in peers],
    )


def test_diff_ignores_unchanged_peers() -> None:
    assert not diff_peers({PUB_B: _peer()}, [_peer()])


def test_diff_detects_new_peer() -> None:
    assert diff_peers({}, [_peer()]) == PeerDelta(upsert=[_peer()], remove=[])


def test_diff_detects_endpoint_change() -> None:
    moved = _peer(endpoint="10.0.0.9:51820")
    assert diff_peers({PUB_B: _peer()}, [moved]) == PeerDelta(upsert=[moved], remove=[])


def test_diff_detects_removed_peer() -> None:
    assert diff_peers({PUB_B: _peer()}, []) == PeerDelta(upsert=[], remove=[PUB_B])


def test_diff_replaces_a_rekeyed_peer() -> None:
    assert diff_peers({PUB_B: _peer()}, [_peer(PUB_B2)]) == PeerDelta(
        upsert=[_peer(PUB_B2)], remove=[PUB_B]
    )


def test_tick_without_changes_never_touches_wg(
    live_server: str, store: BaseStore, tmp_path: Path, wg_calls: list[list[str]]
) -> None:
    agent = _agent(live_server, store, tmp_path)
    agent.tick()
    agent.tick()
    assert wg_calls == []


def test_tick_updates_last_heartbeat(
    live_server: str, store: BaseStore, tmp_path: Path, wg_calls: list[list[str]]
) -> None:
    agent = _agent(live_server, store, tmp_path)
    before = store.nodes()[0].last_heartbeat
    agent.tick()
    assert store.nodes()[0].last_heartbeat > before


def test_new_peer_is_applied_once_and_saved(
    live_server: str, store: BaseStore, tmp_path: Path, wg_calls: list[list[str]]
) -> None:
    agent = _agent(live_server, store, tmp_path)
    store.register(B, PUB_B, "10.0.0.2:51820")

    agent.tick()
    agent.tick()

    assert wg_calls == [
        [
            "wg",
            "set",
            "wg0",
            "peer",
            PUB_B,
            "endpoint",
            "10.0.0.2:51820",
            "allowed-ips",
            "10.100.0.3/32",
            "persistent-keepalive",
            "25",
        ]
    ]
    assert f"PublicKey = {PUB_B}\n" in (tmp_path / "wg0.conf").read_text()


def test_endpoint_change_only_touches_that_peer(
    live_server: str, store: BaseStore, tmp_path: Path, wg_calls: list[list[str]]
) -> None:
    store.register(B, PUB_B, "10.0.0.2:51820")
    store.register(C, PUB_C, "10.0.0.3:51820")
    agent = _agent(live_server, store, tmp_path)

    store.heartbeat(B, "10.0.0.9:51820")
    agent.tick()

    assert len(wg_calls) == 1
    assert PUB_B in wg_calls[0]
    assert "10.0.0.9:51820" in wg_calls[0]


def test_deleted_peer_is_removed(
    live_server: str, store: BaseStore, tmp_path: Path, wg_calls: list[list[str]]
) -> None:
    store.register(B, PUB_B, "10.0.0.2:51820")
    agent = _agent(live_server, store, tmp_path)

    store.delete(B)
    agent.tick()

    assert wg_calls == [["wg", "set", "wg0", "peer", PUB_B, "remove"]]
    assert PUB_B not in (tmp_path / "wg0.conf").read_text()


def test_failed_peer_does_not_block_others_and_is_retried(
    live_server: str,
    store: BaseStore,
    tmp_path: Path,
    wg_calls: list[list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = _agent(live_server, store, tmp_path)
    store.register(B, PUB_B, "10.0.0.2:51820")
    store.register(C, PUB_C, "10.0.0.3:51820")
    applied: list[str] = []
    failing = {PUB_B}

    def set_peer(iface: str, peer: Peer) -> None:
        if peer.pubkey in failing:
            raise subprocess.CalledProcessError(1, ["wg"], stderr="bad endpoint")
        applied.append(peer.pubkey)

    monkeypatch.setattr(wg, "set_peer", set_peer)
    agent.tick()
    assert applied == [PUB_C]

    failing.clear()
    agent.tick()
    assert applied == [PUB_C, PUB_B]


@pytest.mark.parametrize(
    ("pubkey", "endpoint"),
    [
        (PUB_B, "10.0.0.2:51820\n\n[Interface]\nPostUp = touch /tmp/pwned"),
        (PUB_B, "not-an-endpoint"),
        (PUB_B, "10.0.0.2:99999"),
        ("short\nPostUp = touch /tmp/pwned", "10.0.0.2:51820"),
    ],
)
def test_malformed_peers_never_reach_wg_or_the_config(
    live_server: str,
    store: BaseStore,
    tmp_path: Path,
    wg_calls: list[list[str]],
    pubkey: str,
    endpoint: str,
) -> None:
    agent = _agent(live_server, store, tmp_path)
    store.register(B, pubkey, endpoint)
    store.register(C, PUB_C, "10.0.0.3:51820")

    agent.tick()

    assert len(wg_calls) == 1
    assert PUB_C in wg_calls[0]
    assert "PostUp" not in (tmp_path / "wg0.conf").read_text()


def test_run_survives_server_outage(
    live_server: str,
    store: BaseStore,
    tmp_path: Path,
    wg_calls: list[list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = _agent(live_server, store, tmp_path)
    stop = threading.Event()
    outages: list[int] = []

    def tick() -> None:
        outages.append(1)
        if len(outages) == 2:
            stop.set()
        raise requests.ConnectionError

    monkeypatch.setattr(agent, "tick", tick)
    monkeypatch.setattr("client.loop.POLL_INTERVAL_S", 0)
    assert agent.run(stop) == 0
    assert len(outages) == 2


def test_run_stops_when_this_node_is_deleted(
    live_server: str, store: BaseStore, tmp_path: Path, wg_calls: list[list[str]]
) -> None:
    agent = _agent(live_server, store, tmp_path)
    store.delete(A)
    assert agent.run(threading.Event()) == 1
