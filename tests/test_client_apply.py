from __future__ import annotations

import stat
import subprocess
import uuid
from pathlib import Path
from typing import Any

import pytest

from client import wg
from client.api import Peer
from client.cli import main
from client.render import render_config

PEER = Peer(
    node_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
    overlay_ip="10.100.0.3",
    pubkey="pubB",
    endpoint="192.168.1.3:51820",
)


@pytest.fixture()
def calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    recorded: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        recorded.append(args)
        stdout = {"genkey": "privA\n", "pubkey": "A" * 43 + "=\n"}.get(args[1], "")
        return subprocess.CompletedProcess(args, 0, stdout=stdout)

    monkeypatch.setattr(wg.subprocess, "run", run)
    return recorded


def test_render_config_without_peers() -> None:
    assert render_config("privA", "10.100.0.2", 51820, []) == (
        "[Interface]\nPrivateKey = privA\nAddress = 10.100.0.2/24\nListenPort = 51820\n"
    )


def test_render_config_uses_32_allowed_ips_per_peer() -> None:
    config = render_config("privA", "10.100.0.2", 51820, [PEER])
    assert "[Peer]\nPublicKey = pubB\n" in config
    assert "Endpoint = 192.168.1.3:51820\n" in config
    assert "AllowedIPs = 10.100.0.3/32\n" in config
    assert "PersistentKeepalive = 25\n" in config


def test_up_uses_wg_quick_on_a_fresh_host(
    calls: list[list[str]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wg, "interface_exists", lambda iface: False)
    wg.up(tmp_path / "wg0.conf")
    assert calls == [["wg-quick", "up", str(tmp_path / "wg0.conf")]]


def test_up_syncs_without_flapping_an_existing_interface(
    calls: list[list[str]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wg, "interface_exists", lambda iface: True)
    wg.up(tmp_path / "wg0.conf")
    assert ["wg", "syncconf", "wg0", "/dev/stdin"] in calls
    assert not any(call[:2] == ["wg-quick", "up"] for call in calls)


def test_join_writes_private_config_and_brings_it_up(
    live_server: str, calls: list[list[str]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wg, "interface_exists", lambda iface: False)
    args = ["join", "--server", live_server, "--key", "testkey", "--state-dir", str(tmp_path)]
    assert main(args) == 0

    config = tmp_path / "wg0.conf"
    assert "Address = 10.100.0.2/24\n" in config.read_text()
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert ["wg-quick", "up", str(config)] in calls


def test_private_key_never_reaches_argv(
    live_server: str, calls: list[list[str]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wg, "interface_exists", lambda iface: True)
    args = ["join", "--server", live_server, "--key", "testkey", "--state-dir", str(tmp_path)]
    assert main(args) == 0
    assert not any("privA" in part for call in calls for part in call)


def test_down_is_a_noop_without_interface(
    calls: list[list[str]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wg, "interface_exists", lambda iface: False)
    assert main(["down", "--state-dir", str(tmp_path)]) == 0
    assert calls == []
