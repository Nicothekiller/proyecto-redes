from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from server.config import FIRST_HOST_SUFFIX, LAST_HOST_SUFFIX, OVERLAY_NET
from server.store.base import (
    BaseStore,
    DuplicatePubkeyError,
    PeerRecord,
    PoolExhaustedError,
    UnknownNodeError,
)
from server.store.db import init_db, session_scope
from server.store.models import Node


def _to_peer(node: Node) -> PeerRecord:
    return PeerRecord(
        node_id=node.node_id,
        overlay_ip=node.overlay_ip,
        pubkey=node.pubkey,
        endpoint=node.endpoint,
    )


class SQLiteStore(BaseStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()

        init_db()

    def _allocate_ip(self, session: Session) -> str:
        used = {int(ip.split(".")[-1]) for ip in session.scalars(select(Node.overlay_ip))}
        for suffix in range(FIRST_HOST_SUFFIX, LAST_HOST_SUFFIX + 1):
            if suffix not in used:
                return str(OVERLAY_NET[suffix])
        raise PoolExhaustedError("overlay pool exhausted")

    def register(
        self, node_id: uuid.UUID, pubkey: str, endpoint: str
    ) -> tuple[str, list[PeerRecord]]:
        with self._lock:
            with session_scope() as session:
                holder = session.scalar(select(Node).where(Node.pubkey == pubkey))
                if holder is not None and holder.node_id != node_id:
                    raise DuplicatePubkeyError(
                        f"pubkey already registered to node {holder.node_id}"
                    )

                node = session.get(Node, node_id)
                if node is not None:
                    node.pubkey = pubkey
                    node.endpoint = endpoint
                    node.last_heartbeat = datetime.now(UTC)
                else:
                    overlay_ip = self._allocate_ip(session)
                    node = Node(
                        node_id=node_id,
                        pubkey=pubkey,
                        overlay_ip=overlay_ip,
                        endpoint=endpoint,
                        last_heartbeat=datetime.now(UTC),
                    )
                    session.add(node)
                session.flush()
                peers = [
                    _to_peer(i)
                    for i in session.scalars(
                        select(Node).where(Node.node_id != node_id).order_by(Node.overlay_ip)
                    ).all()
                ]
                return node.overlay_ip, peers

    def peers(self, node_id: uuid.UUID) -> list[PeerRecord]:
        with session_scope() as session:
            node = session.get(Node, node_id)

            if node is None:
                raise UnknownNodeError("Node isn't registered in the system")

            # couldnt stop myself from making the 1 liner
            return [
                _to_peer(i)
                for i in session.scalars(
                    select(Node).where(Node.node_id != node_id).order_by(Node.overlay_ip)
                ).all()
            ]

    def heartbeat(self, node_id: uuid.UUID, endpoint: str | None = None) -> None:
        with session_scope() as session:
            node = session.get(Node, node_id)

            if node is None:
                raise UnknownNodeError("Node isn't registered in the system")

            node.last_heartbeat = datetime.now(UTC)
            if endpoint is not None:
                node.endpoint = endpoint

    def delete(self, node_id: uuid.UUID) -> None:
        with self._lock:
            with session_scope() as session:
                node = session.get(Node, node_id)

                if node is None:
                    raise UnknownNodeError("Node isn't registered in the system")

                session.delete(node)
                session.flush()
