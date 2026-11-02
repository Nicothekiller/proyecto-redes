from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from client import probe, stats, wg
from client.api import Peer, PeerReport, ServerClient
from client.loop import Agent
from client.probe import ProbeResult
from client.state import NodeState
from client.stats import PeerStats, parse_endpoints, parse_handshakes, parse_transfer
from server.store.base import BaseStore

A = uuid.UUID("11111111-1111-1111-1111-111111111111")
B = uuid.UUID("22222222-2222-2222-2222-222222222222")
PUB_A = "A" * 43 + "="
PUB_B = "B" * 43 + "="
PRIVATE_KEY = "S" * 43 + "="
AUTH = {"Authorization": "Bearer testkey"}
FORBIDDEN = ("private", "preshared")


def _agent(live_server: str, store: BaseStore, tmp_path: Path) -> Agent:
    overlay_ip, peers = store.register(A, PUB_A, "127.0.0.1:51820")
    return Agent(
        ServerClient(live_server, "testkey"),
        live_server,
        NodeState(node_id=A, overlay_ip=overlay_ip),
        PRIVATE_KEY,
        tmp_path / "wg0.conf",
        [Peer(p.node_id, p.overlay_ip, p.pubkey, p.endpoint) for p in peers],
    )


def _fake_wg_show(monkeypatch: pytest.MonkeyPatch, pubkey: str = PUB_B) -> None:
    outputs = {
        "latest-handshakes": f"{pubkey}\t1700000000\n",
        "transfer": f"{pubkey}\t100\t200\n",
        "endpoints": f"{pubkey}\t10.0.0.2:51820\n",
    }
    monkeypatch.setattr(wg, "show", lambda iface, field: outputs[field])


def test_parsers_read_wg_show_output() -> None:
    assert parse_handshakes("k1\t1700000000\nk2\t0\n") == {"k1": 1700000000, "k2": 0}
    assert parse_transfer("k1\t10\t20\n") == {"k1": (10, 20)}
    assert parse_endpoints("k1\t10.0.0.2:51820\nk2\t(none)\n") == {
        "k1": "10.0.0.2:51820",
        "k2": None,
    }


def test_parsers_accept_an_interface_without_peers() -> None:
    assert parse_handshakes("") == {}
    assert parse_transfer("") == {}
    assert parse_endpoints("") == {}


def test_collect_never_uses_wg_show_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    fields: list[str] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        fields.append(args[3])
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(wg.subprocess, "run", run)
    stats.collect("wg0")
    assert sorted(fields) == ["endpoints", "latest-handshakes", "transfer"]


def test_collect_merges_the_three_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_wg_show(monkeypatch)
    assert stats.collect("wg0") == {
        PUB_B: PeerStats(
            last_handshake=1700000000, rx_bytes=100, tx_bytes=200, endpoint="10.0.0.2:51820"
        )
    }


def test_report_only_carries_the_fields_the_server_accepts() -> None:
    report = PeerReport(peer_id=B, last_handshake=0, rx_bytes=1, tx_bytes=2)
    assert report.to_json() == {
        "peer_id": str(B),
        "last_handshake": 0,
        "rx_bytes": 1,
        "tx_bytes": 2,
    }


def test_probe_reads_rtt(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = "64 bytes from 10.100.0.3: icmp_seq=1 ttl=64 time=0.72 ms\n"
    monkeypatch.setattr(
        probe.subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout=stdout),
    )
    assert probe.probe("10.100.0.3") == ProbeResult(ok=True, rtt_ms=0.72)


def test_probe_reports_failure_without_rtt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        probe.subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 1, stdout=""),
    )
    assert probe.probe("10.100.0.3") == ProbeResult(ok=False)


def test_probe_all_handles_no_peers() -> None:
    assert probe.probe_all([]) == {}


def test_tick_reports_proven_connectivity_to_the_dashboard(
    live_server: str,
    client: TestClient,
    store: BaseStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store.register(B, PUB_B, "10.0.0.2:51820")
    agent = _agent(live_server, store, tmp_path)
    _fake_wg_show(monkeypatch)
    monkeypatch.setattr(probe, "probe_all", lambda ips: {ip: ProbeResult(True, 0.5) for ip in ips})

    agent.tick()

    pair = client.get("/status", headers=AUTH).json()["pairs"][0]
    assert pair["reporter"] == str(A)
    assert pair["peer"] == str(B)
    assert pair["rx_bytes"] == 100
    assert pair["probe_ok"] is True
    assert pair["connectivity_proven"] is True


def test_failed_probe_is_reported_as_not_proven(
    live_server: str,
    client: TestClient,
    store: BaseStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store.register(B, PUB_B, "10.0.0.2:51820")
    agent = _agent(live_server, store, tmp_path)
    _fake_wg_show(monkeypatch)
    monkeypatch.setattr(probe, "probe_all", lambda ips: {ip: ProbeResult(False) for ip in ips})

    agent.tick()

    pair = client.get("/status", headers=AUTH).json()["pairs"][0]
    assert pair["probe_ok"] is False
    assert pair["connectivity_proven"] is False


def test_peer_deleted_mid_tick_does_not_lose_the_heartbeat(
    live_server: str,
    store: BaseStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store.register(B, PUB_B, "10.0.0.2:51820")
    agent = _agent(live_server, store, tmp_path)
    _fake_wg_show(monkeypatch)
    monkeypatch.setattr(probe, "probe_all", lambda ips: {ip: ProbeResult(True, 0.5) for ip in ips})
    monkeypatch.setattr(wg, "remove_peer", lambda iface, pubkey: None)
    store.delete(B)
    before = store.nodes()[0].last_heartbeat

    agent.tick()

    assert store.nodes()[0].last_heartbeat > before
    assert PUB_B not in (tmp_path / "wg0.conf").read_text()


def test_nothing_secret_leaves_the_node(
    live_server: str,
    store: BaseStore,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from client import api

    store.register(B, PUB_B, "10.0.0.2:51820")
    agent = _agent(live_server, store, tmp_path)
    _fake_wg_show(monkeypatch)
    monkeypatch.setattr(probe, "probe_all", lambda ips: {ip: ProbeResult(True, 0.5) for ip in ips})

    sent: list[Any] = []
    original = api.requests.Session.request

    def spy(self: Any, method: str, url: str, **kwargs: Any) -> Any:
        sent.append(kwargs.get("json"))
        return original(self, method, url, **kwargs)

    monkeypatch.setattr(api.requests.Session, "request", spy)
    agent.tick()

    payload = json.dumps(sent).lower() + caplog.text.lower()
    assert PRIVATE_KEY.lower() not in payload
    assert not any(word in payload for word in FORBIDDEN)
