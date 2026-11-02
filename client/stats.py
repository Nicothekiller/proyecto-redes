from __future__ import annotations

from dataclasses import dataclass

from client import wg


@dataclass(frozen=True)
class PeerStats:
    last_handshake: int
    rx_bytes: int
    tx_bytes: int
    endpoint: str | None


def _rows(text: str) -> list[list[str]]:
    return [line.split("\t") for line in text.splitlines() if line]


def parse_handshakes(text: str) -> dict[str, int]:
    return {pubkey: int(seconds) for pubkey, seconds in _rows(text)}


def parse_transfer(text: str) -> dict[str, tuple[int, int]]:
    return {pubkey: (int(rx), int(tx)) for pubkey, rx, tx in _rows(text)}


def parse_endpoints(text: str) -> dict[str, str | None]:
    return {pubkey: None if endpoint == "(none)" else endpoint for pubkey, endpoint in _rows(text)}


def collect(iface: str) -> dict[str, PeerStats]:
    handshakes = parse_handshakes(wg.show(iface, "latest-handshakes"))
    transfer = parse_transfer(wg.show(iface, "transfer"))
    endpoints = parse_endpoints(wg.show(iface, "endpoints"))
    return {
        pubkey: PeerStats(
            last_handshake=seconds,
            rx_bytes=transfer[pubkey][0],
            tx_bytes=transfer[pubkey][1],
            endpoint=endpoints.get(pubkey),
        )
        for pubkey, seconds in handshakes.items()
        if pubkey in transfer
    }
