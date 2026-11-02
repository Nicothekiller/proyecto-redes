from __future__ import annotations

import logging
import subprocess
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path

import requests

from client import netinfo, probe, stats, wg
from client.api import Peer, PeerReport, ServerClient, UnknownNodeError
from client.config import ENDPOINT_CHECK_S, POLL_INTERVAL_S
from client.render import render_config
from client.state import NodeState, save_state, write_private

log = logging.getLogger("client")


@dataclass(frozen=True)
class PeerDelta:
    upsert: list[Peer]
    remove: list[str]

    def __bool__(self) -> bool:
        return bool(self.upsert or self.remove)


def diff_peers(current: dict[str, Peer], desired: list[Peer]) -> PeerDelta:
    wanted = {peer.pubkey: peer for peer in desired}
    return PeerDelta(
        upsert=[peer for key, peer in wanted.items() if current.get(key) != peer],
        remove=[key for key in current if key not in wanted],
    )


class Agent:
    def __init__(
        self,
        server: ServerClient,
        base_url: str,
        state: NodeState,
        private_key: str,
        config_path: Path,
        peers: list[Peer],
    ) -> None:
        self._server = server
        self._base_url = base_url
        self._state = state
        self._private_key = private_key
        self._config_path = config_path
        self._iface = config_path.stem
        self._peers = {peer.pubkey: peer for peer in peers}
        self._reported_endpoint: str | None = None

    def _endpoint(self) -> str:
        port = wg.show(self._iface, "listen-port")
        return f"{netinfo.local_ip_towards(self._base_url)}:{port}"

    def _endpoint_changed(self) -> bool:
        try:
            endpoint = self._endpoint()
        except (OSError, subprocess.CalledProcessError):
            return False
        if endpoint == self._reported_endpoint:
            return False
        log.info("endpoint changed: %s -> %s", self._reported_endpoint, endpoint)
        return True

    def _remember_listen_port(self, endpoint: str) -> None:
        port = int(endpoint.rpartition(":")[2])
        if port != self._state.listen_port:
            self._state = replace(self._state, listen_port=port)
            save_state(self._config_path.parent, self._state)
            self._write_config()

    def _apply(self, delta: PeerDelta) -> None:
        for pubkey in delta.remove:
            try:
                wg.remove_peer(self._iface, pubkey)
            except subprocess.CalledProcessError as exc:
                log.warning("could not remove a peer: %s", exc.stderr.strip())
                continue
            log.info("removed peer %s", self._peers.pop(pubkey).overlay_ip)
        for peer in delta.upsert:
            try:
                wg.set_peer(self._iface, peer)
            except subprocess.CalledProcessError as exc:
                log.warning("could not apply peer %s: %s", peer.overlay_ip, exc.stderr.strip())
                continue
            self._peers[peer.pubkey] = peer
            log.info("applied peer %s at %s", peer.overlay_ip, peer.endpoint)

    def _write_config(self) -> None:
        if self._state.overlay_ip is None:
            raise ValueError("node has no overlay ip")
        write_private(
            self._config_path,
            render_config(
                self._private_key,
                self._state.overlay_ip,
                self._state.listen_port,
                list(self._peers.values()),
            ),
        )

    def _reports(self) -> list[PeerReport]:
        peer_stats = stats.collect(self._iface)
        known = {pubkey: peer for pubkey, peer in self._peers.items() if pubkey in peer_stats}
        probes = probe.probe_all([peer.overlay_ip for peer in known.values()])
        return [
            PeerReport(
                peer_id=peer.node_id,
                last_handshake=peer_stats[pubkey].last_handshake,
                rx_bytes=peer_stats[pubkey].rx_bytes,
                tx_bytes=peer_stats[pubkey].tx_bytes,
                endpoint=peer_stats[pubkey].endpoint,
                probe_ok=probes[peer.overlay_ip].ok,
                probe_rtt_ms=probes[peer.overlay_ip].rtt_ms,
            )
            for pubkey, peer in known.items()
        ]

    def _heartbeat(self) -> None:
        endpoint = self._endpoint()
        reports = self._reports()
        try:
            self._server.heartbeat(self._state.node_id, endpoint, reports)
        except UnknownNodeError:
            if not reports:
                raise
            self._server.heartbeat(self._state.node_id, endpoint)
        self._reported_endpoint = endpoint
        self._remember_listen_port(endpoint)

    def tick(self) -> None:
        self._heartbeat()
        delta = diff_peers(self._peers, self._server.peers(self._state.node_id))
        if delta:
            self._apply(delta)
            self._write_config()

    def _sleep(self, started: float, stop: threading.Event) -> bool:
        deadline = started + POLL_INTERVAL_S
        while (remaining := deadline - time.monotonic()) > 0:
            if stop.wait(min(ENDPOINT_CHECK_S, remaining)):
                return True
            if self._endpoint_changed():
                return False
        return stop.is_set()

    def run(self, stop: threading.Event) -> int:
        while True:
            started = time.monotonic()
            try:
                self.tick()
            except UnknownNodeError:
                log.error("this node was deleted from the server")
                return 1
            except (requests.RequestException, OSError) as exc:
                log.warning("server unreachable, keeping current tunnels: %s", type(exc).__name__)
            except subprocess.CalledProcessError as exc:
                log.warning("%s failed: %s", exc.cmd[0], exc.stderr.strip())
            if self._sleep(started, stop):
                return 0
