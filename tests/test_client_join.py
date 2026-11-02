from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

from client import wg
from client.api import server_url
from client.cli import main
from client.state import NodeState, load_or_create_state, save_state


@pytest.fixture()
def fake_wg(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["wg", "genkey"]:
            return subprocess.CompletedProcess(args, 0, stdout=f"private-{len(calls)}\n")
        if args == ["wg", "pubkey"]:
            return subprocess.CompletedProcess(args, 0, stdout="Q" * 43 + "=\n")
        if args[0] == "wg-quick":
            return subprocess.CompletedProcess(args, 0, stdout="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(wg.subprocess, "run", run)
    monkeypatch.setattr(wg, "interface_exists", lambda iface: False)
    return calls


def _join(server: str, state_dir: Path) -> int:
    return main(["join", "--server", server, "--key", "testkey", "--state-dir", str(state_dir)])


def test_state_is_created_once(tmp_path: Path) -> None:
    first = load_or_create_state(tmp_path)
    second = load_or_create_state(tmp_path)
    assert first == second


def test_state_round_trips_overlay_ip(tmp_path: Path) -> None:
    state = load_or_create_state(tmp_path).with_overlay_ip("10.100.0.2")
    save_state(tmp_path, state)
    assert load_or_create_state(tmp_path) == state


def test_listen_port_of_saved_state_wins(tmp_path: Path) -> None:
    load_or_create_state(tmp_path, listen_port=51000)
    assert load_or_create_state(tmp_path, listen_port=52000).listen_port == 51000


def test_private_key_is_reused_and_private(tmp_path: Path, fake_wg: list[list[str]]) -> None:
    first = wg.load_or_create_private_key(tmp_path)
    second = wg.load_or_create_private_key(tmp_path)
    assert first == second
    assert fake_wg == [["wg", "genkey"]]


def test_private_files_are_0600(tmp_path: Path, fake_wg: list[list[str]]) -> None:
    wg.load_or_create_private_key(tmp_path)
    save_state(tmp_path, NodeState(node_id=load_or_create_state(tmp_path).node_id))
    for name in ("privatekey", "state.json"):
        assert stat.S_IMODE((tmp_path / name).stat().st_mode) == 0o600


@pytest.mark.parametrize(
    ("server", "expected"),
    [
        ("192.168.1.10", "http://192.168.1.10:8000"),
        ("192.168.1.10:9000", "http://192.168.1.10:9000"),
        ("http://server.lan", "http://server.lan:8000"),
        ("https://server.lan:8443/", "https://server.lan:8443"),
    ],
)
def test_server_url(server: str, expected: str) -> None:
    assert server_url(server) == expected


def test_join_twice_keeps_identity_and_ip(
    live_server: str, tmp_path: Path, fake_wg: list[list[str]]
) -> None:
    assert _join(live_server, tmp_path) == 0
    first = json.loads((tmp_path / "state.json").read_text())
    key = (tmp_path / "privatekey").read_text()

    assert _join(live_server, tmp_path) == 0
    second = json.loads((tmp_path / "state.json").read_text())

    assert first == second
    assert first["overlay_ip"] == "10.100.0.2"
    assert (tmp_path / "privatekey").read_text() == key


def test_join_only_sends_public_material(
    live_server: str,
    tmp_path: Path,
    fake_wg: list[list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from client import api

    sent: list[dict[str, Any]] = []
    original = api.requests.Session.request

    def spy(self: Any, method: str, url: str, **kwargs: Any) -> Any:
        sent.append(kwargs["json"])
        return original(self, method, url, **kwargs)

    monkeypatch.setattr(api.requests.Session, "request", spy)
    assert _join(live_server, tmp_path) == 0

    private_key = (tmp_path / "privatekey").read_text()
    assert set(sent[0]) == {"node_id", "pubkey", "endpoint"}
    assert private_key not in json.dumps(sent)


def test_join_without_key_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)
    args = ["join", "--server", "127.0.0.1", "--key", "", "--state-dir", str(tmp_path)]
    assert main(args) == 2
