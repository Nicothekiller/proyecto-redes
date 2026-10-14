from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

from server.config import FIRST_HOST_SUFFIX, LAST_HOST_SUFFIX, OVERLAY_NET
from server.store.base import (
    BaseStore,
    DuplicatePubkeyError,
    NodeRecord,
    PeerRecord,
    PoolExhaustedError,
    UnknownNodeError,
)


class InMemoryStore(BaseStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nodes: dict[uuid.UUID, NodeRecord] = {}
        self._pubkey_index: dict[str, uuid.UUID] = {}
        self._next_host = FIRST_HOST_SUFFIX
        self._free_hosts: list[int] = []

    def _allocate_ip(self) -> str:
        if self._free_hosts:
            suffix = self._free_hosts.pop()
        else:
            if self._next_host > LAST_HOST_SUFFIX:
                raise PoolExhaustedError("overlay pool exhausted")
            suffix = self._next_host
            self._next_host += 1
        return str(OVERLAY_NET[suffix])

    def register(
        self, node_id: uuid.UUID, pubkey: str, endpoint: str
    ) -> tuple[str, list[PeerRecord]]:
        with self._lock:
            holder = self._pubkey_index.get(pubkey)
            if holder is not None and holder != node_id and not self._nodes[holder].deleted:
                raise DuplicatePubkeyError(f"pubkey already registered to node {holder}")
            node = self._nodes.get(node_id)
            if node is not None and not node.deleted:
                if node.pubkey != pubkey:
                    self._pubkey_index.pop(node.pubkey, None)
                    self._pubkey_index[pubkey] = node_id
                node.pubkey = pubkey
                node.endpoint = endpoint
            else:
                overlay_ip = self._allocate_ip()
                node = NodeRecord(
                    pubkey=pubkey,
                    overlay_ip=overlay_ip,
                    endpoint=endpoint,
                    last_heartbeat=datetime.now(UTC),
                )
                self._nodes[node_id] = node
                self._pubkey_index[pubkey] = node_id
            peers = sorted(
                [
                    PeerRecord(
                        node_id=nid,
                        overlay_ip=n.overlay_ip,
                        pubkey=n.pubkey,
                        endpoint=n.endpoint,
                    )
                    for nid, n in self._nodes.items()
                    if nid != node_id and not n.deleted
                ],
                key=lambda r: r.overlay_ip,
            )
            return node.overlay_ip, peers

    def peers(self, node_id: uuid.UUID) -> list[PeerRecord]:
        """Returns every non-deleted node except the requester, sorted by overlay_ip.

        Raises UnknownNodeError if the requester is unknown or deleted.
        """
        with self._lock:
            if node_id not in self._nodes or self._nodes[node_id].deleted:
                raise UnknownNodeError("Node isn't registered in the system")

            return sorted(
                [
                    PeerRecord(
                        node_id=nid,
                        overlay_ip=node.overlay_ip,
                        pubkey=node.pubkey,
                        endpoint=node.endpoint,
                    )
                    for nid, node in self._nodes.items()
                    if not node.deleted and nid != node_id
                ],
                key=lambda r: r.overlay_ip,
            )

    def heartbeat(self, node_id: uuid.UUID, endpoint: str | None = None) -> None:
        """Updates when a node was last seen, and its endpoint if given.

        Raises UnknownNodeError if the node is unknown or deleted.
        """
        with self._lock:
            if node_id not in self._nodes or self._nodes[node_id].deleted:
                raise UnknownNodeError("Node isn't registered in the system")

            self._nodes[node_id].last_heartbeat = datetime.now(UTC)

            if endpoint is not None:
                self._nodes[node_id].endpoint = endpoint
