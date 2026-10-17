from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class PoolExhaustedError(Exception):
    pass


class DuplicatePubkeyError(Exception):
    pass


class UnknownNodeError(Exception):
    pass


@dataclass(frozen=True)
class PeerRecord:
    node_id: uuid.UUID
    overlay_ip: str
    pubkey: str
    endpoint: str


@dataclass(frozen=True)
class NodeRecord:
    node_id: uuid.UUID
    overlay_ip: str
    pubkey: str
    endpoint: str
    last_heartbeat: datetime


@dataclass(frozen=True)
class PeerReportRecord:
    """A client's report about one peer. `last_handshake` is epoch seconds, 0 = never."""

    peer_id: uuid.UUID
    last_handshake: int
    rx_bytes: int
    tx_bytes: int
    endpoint: str | None = None
    probe_ok: bool | None = None
    probe_rtt_ms: float | None = None


@dataclass(frozen=True)
class PairRecord:
    """A directed report, from `reporter` about `peer`."""

    reporter: uuid.UUID
    peer: uuid.UUID
    reporter_overlay_ip: str
    peer_overlay_ip: str
    endpoint: str | None
    last_handshake: int
    rx_bytes: int
    tx_bytes: int
    probe_ok: bool | None
    probe_rtt_ms: float | None
    probe_ran_at: datetime | None
    reported_at: datetime


class BaseStore(ABC):
    @abstractmethod
    def register(
        self, node_id: uuid.UUID, pubkey: str, endpoint: str
    ) -> tuple[str, list[PeerRecord]]:
        """Idempotent join: known node_id returns its same overlay_ip.

        Returns (overlay_ip, peers) where peers lists every other
        node.

        Raises DuplicatePubkeyError if pubkey belongs to another node.
        """

    @abstractmethod
    def peers(self, node_id: uuid.UUID) -> list[PeerRecord]:
        """Returns every node except the requester, sorted by overlay_ip.

        Raises UnknownNodeError if the requester is unknown.
        """

    @abstractmethod
    def heartbeat(
        self,
        node_id: uuid.UUID,
        endpoint: str | None = None,
        peers: list[PeerReportRecord] | None = None,
    ) -> None:
        """Updates when a node was last seen, and its endpoint if given.

        Each `peers` entry upserts one directed reporter->peer row and stamps
        `reported_at` (plus `probe_ran_at` when a probe result is present) with
        the server clock.

        Raises UnknownNodeError if the node or any reported peer is unknown.
        """

    @abstractmethod
    def delete(self, node_id: uuid.UUID) -> None:
        """Deletes a node from the system.

        Raises UnknownNodeError if node doesnt exist.
        """

    @abstractmethod
    def nodes(self) -> list[NodeRecord]:
        """Returns a list of all nodes with their full data."""

    @abstractmethod
    def pairs(self) -> list[PairRecord]:
        """Returns every directed reporter->peer report.

        Sorted by (reporter_overlay_ip, peer_overlay_ip). Pairs with no report
        yet are absent, not returned with nulls.
        """
