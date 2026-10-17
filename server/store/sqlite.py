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
    NodeRecord,
    PairRecord,
    PeerRecord,
    PeerReportRecord,
    PoolExhaustedError,
    UnknownNodeError,
)
from server.store.db import init_db, session_scope
from server.store.models import Node, PeerStatus


def _to_peer(node: Node) -> PeerRecord:
    return PeerRecord(
        node_id=node.node_id,
        overlay_ip=node.overlay_ip,
        pubkey=node.pubkey,
        endpoint=node.endpoint,
    )


def _to_node_record(node: Node) -> NodeRecord:
    return NodeRecord(
        node_id=node.node_id,
        overlay_ip=node.overlay_ip,
        pubkey=node.pubkey,
        endpoint=node.endpoint,
        last_heartbeat=node.last_heartbeat,
    )


def _to_pair_record(ps: PeerStatus, session: Session) -> PairRecord:
    reporter = session.get(Node, ps.reporter_node_id)
    peer = session.get(Node, ps.peer_node_id)
    if reporter is None or peer is None:
        raise UnknownNodeError("peer status references an unknown node")

    return PairRecord(
        reporter=ps.reporter_node_id,
        peer=ps.peer_node_id,
        reporter_overlay_ip=reporter.overlay_ip,
        peer_overlay_ip=peer.overlay_ip,
        endpoint=ps.endpoint,
        last_handshake=ps.last_handshake,
        rx_bytes=ps.rx_bytes,
        tx_bytes=ps.tx_bytes,
        probe_ok=ps.probe_ok,
        probe_rtt_ms=ps.probe_rtt_ms,
        probe_ran_at=ps.probe_ran_at,
        reported_at=ps.reported_at,
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

    def heartbeat(
        self,
        node_id: uuid.UUID,
        endpoint: str | None = None,
        peers: list[PeerReportRecord] | None = None,
    ) -> None:
        with session_scope() as session:
            node = session.get(Node, node_id)

            if node is None:
                raise UnknownNodeError("Node isn't registered in the system")

            now = datetime.now(UTC)
            node.last_heartbeat = now
            if endpoint is not None:
                node.endpoint = endpoint

            if peers is not None:
                for record in peers:
                    if session.get(Node, record.peer_id) is None:
                        raise UnknownNodeError(f"peer {record.peer_id} isn't registered")

                    row = session.get(PeerStatus, (node_id, record.peer_id))
                    if row is None:
                        row = PeerStatus(reporter_node_id=node_id, peer_node_id=record.peer_id)
                        session.add(row)

                    if record.endpoint is not None:
                        row.endpoint = record.endpoint

                    row.last_handshake = record.last_handshake
                    row.rx_bytes = record.rx_bytes
                    row.tx_bytes = record.tx_bytes
                    row.reported_at = now

                    if record.probe_ok is not None:
                        row.probe_ok = record.probe_ok
                        row.probe_rtt_ms = record.probe_rtt_ms
                        row.probe_ran_at = now

    def delete(self, node_id: uuid.UUID) -> None:
        with self._lock:
            with session_scope() as session:
                node = session.get(Node, node_id)

                if node is None:
                    raise UnknownNodeError("Node isn't registered in the system")

                session.delete(node)
                session.flush()

    def nodes(self) -> list[NodeRecord]:
        with session_scope() as session:
            return [
                _to_node_record(i)
                for i in session.scalars(select(Node).order_by(Node.overlay_ip)).all()
            ]

    def pairs(self) -> list[PairRecord]:
        with session_scope() as session:
            rows = session.scalars(select(PeerStatus)).all()
            return sorted(
                [_to_pair_record(row, session) for row in rows],
                key=lambda pair: (
                    tuple(int(part) for part in pair.reporter_overlay_ip.split(".")),
                    tuple(int(part) for part in pair.peer_overlay_ip.split(".")),
                ),
            )
