from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from server.auth import require_auth
from server.config import OFFLINE_AFTER_S, PROBE_TTL_S
from server.schemas import NodeOut, PairOut, StatusOut
from server.store import get_store
from server.store.base import NodeRecord, PairRecord

router = APIRouter(tags=["dashboard"])


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _connectivity_proven(pair: PairRecord, now: datetime) -> bool:
    return bool(
        pair.probe_ok
        and pair.probe_ran_at is not None
        and (now - _as_utc(pair.probe_ran_at)).total_seconds() <= PROBE_TTL_S
    )


def _to_node_out(node: NodeRecord, pairs: list[PairRecord], now: datetime) -> NodeOut:
    age = (now - _as_utc(node.last_heartbeat)).total_seconds()
    return NodeOut(
        node_id=node.node_id,
        overlay_ip=node.overlay_ip,
        pubkey=node.pubkey,
        endpoint=node.endpoint,
        last_heartbeat=_as_utc(node.last_heartbeat),
        heartbeat_recent=age <= OFFLINE_AFTER_S,
        heartbeat_age_s=age,
        connectivity_proven=any(
            (pair.reporter == node.node_id or pair.peer == node.node_id)
            and _connectivity_proven(pair, now)
            for pair in pairs
        ),
    )


def _to_pair_out(pair: PairRecord, now: datetime) -> PairOut:
    age = now.timestamp() - pair.last_handshake if pair.last_handshake > 0 else None
    return PairOut(
        reporter=pair.reporter,
        peer=pair.peer,
        reporter_overlay_ip=pair.reporter_overlay_ip,
        peer_overlay_ip=pair.peer_overlay_ip,
        endpoint=pair.endpoint,
        last_handshake=pair.last_handshake,
        handshake_age_s=age,
        rx_bytes=pair.rx_bytes,
        tx_bytes=pair.tx_bytes,
        probe_ok=pair.probe_ok,
        probe_rtt_ms=pair.probe_rtt_ms,
        probe_ran_at=_as_utc(pair.probe_ran_at) if pair.probe_ran_at is not None else None,
        connectivity_proven=_connectivity_proven(pair, now),
    )


@router.get("/nodes", response_model=list[NodeOut])
def nodes(_auth: bool = Depends(require_auth)) -> list[NodeOut]:
    store = get_store()
    now = datetime.now(UTC)
    pairs = store.pairs()
    return [_to_node_out(node, pairs, now) for node in store.nodes()]


@router.get("/status", response_model=StatusOut)
def status(_auth: bool = Depends(require_auth)) -> StatusOut:
    store = get_store()
    now = datetime.now(UTC)
    nodes_total = len(store.nodes())
    return StatusOut(
        as_of=now,
        offline_after_s=OFFLINE_AFTER_S,
        probe_ttl_s=PROBE_TTL_S,
        nodes_total=nodes_total,
        pairs=[_to_pair_out(pair, now) for pair in store.pairs()],
    )
