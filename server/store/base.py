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


@dataclass
class NodeRecord:
    pubkey: str
    overlay_ip: str
    endpoint: str
    last_heartbeat: datetime
    deleted: bool = False


class BaseStore(ABC):
    @abstractmethod
    def register(
        self, node_id: uuid.UUID, pubkey: str, endpoint: str
    ) -> tuple[str, list[PeerRecord]]:
        """Idempotent join: known node_id returns its same overlay_ip.

        Returns (overlay_ip, peers) where peers lists every other
        non-deleted node.

        Raises DuplicatePubkeyError if pubkey belongs to another
        non-deleted node.
        """

    @abstractmethod
    def peers(self, node_id: uuid.UUID) -> list[PeerRecord]:
        """Returns every non-deleted node except the requester, sorted by overlay_ip.

        Raises UnknownNodeError if the requester is unknown or deleted.
        """

    @abstractmethod
    def heartbeat(self, node_id: uuid.UUID, endpoint: str | None = None) -> None:
        """Updates when a node was last seen, and its endpoint if given.

        Raises UnknownNodeError if the node is unknown or deleted.
        """
