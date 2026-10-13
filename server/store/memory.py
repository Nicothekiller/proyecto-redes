from __future__ import annotations

import threading
from datetime import UTC, datetime

from server.config import FIRST_HOST_SUFFIX, LAST_HOST_SUFFIX, OVERLAY_NET
from server.store.base import (
    BaseStore,
    DuplicatePubkeyError,
    NodeRecord,
    PeerRecord,
    PoolExhaustedError,
)


class InMemoryStore(BaseStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nodes: dict[str, NodeRecord] = {}
        self._pubkey_index: dict[str, str] = {}
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

    def register(self, node_id: str, pubkey: str, endpoint: str) -> tuple[str, list[PeerRecord]]:
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
                    last_heartbeat=datetime.now(UTC).isoformat(),
                )
                self._nodes[node_id] = node
                self._pubkey_index[pubkey] = node_id
            peers = [
                PeerRecord(
                    node_id=nid,
                    overlay_ip=n.overlay_ip,
                    pubkey=n.pubkey,
                    endpoint=n.endpoint,
                )
                for nid, n in self._nodes.items()
                if nid != node_id and not n.deleted
            ]
            return node.overlay_ip, peers
