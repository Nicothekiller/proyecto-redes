from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class PoolExhaustedError(Exception):
    pass


class DuplicatePubkeyError(Exception):
    pass


@dataclass(frozen=True)
class PeerRecord:
    node_id: str
    overlay_ip: str
    pubkey: str
    endpoint: str


@dataclass
class NodeRecord:
    pubkey: str
    overlay_ip: str
    endpoint: str
    last_heartbeat: str
    deleted: bool = False


class BaseStore(ABC):
    @abstractmethod
    def register(self, node_id: str, pubkey: str, endpoint: str) -> tuple[str, list[PeerRecord]]:
        """Idempotent join: known node_id returns its same overlay_ip.

        Returns (overlay_ip, peers) where peers lists every other
        non-deleted node.

        Raises DuplicatePubkeyError if pubkey belongs to another
        non-deleted node.
        """
