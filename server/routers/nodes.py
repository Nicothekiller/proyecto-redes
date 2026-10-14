from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from server.auth import require_auth
from server.schemas import HeartbeatIn, PeerOut, RegisterIn, RegisterOut
from server.store import get_store

router = APIRouter(tags=["nodes"])


@router.post("/register", response_model=RegisterOut)
def register(body: RegisterIn, _auth: bool = Depends(require_auth)) -> RegisterOut:
    store = get_store()
    overlay_ip, peers = store.register(body.node_id, body.pubkey, body.endpoint)
    return RegisterOut(
        overlay_ip=overlay_ip,
        peers=[PeerOut.model_validate(p, from_attributes=True) for p in peers],
    )


@router.get("/peers", response_model=list[PeerOut])
def peers(node_id: uuid.UUID, _auth: bool = Depends(require_auth)) -> list[PeerOut]:
    return [
        PeerOut.model_validate(peer, from_attributes=True) for peer in get_store().peers(node_id)
    ]


@router.post("/heartbeat", status_code=204)
def heartbeat(body: HeartbeatIn, _auth: bool = Depends(require_auth)) -> None:
    get_store().heartbeat(body.node_id, body.endpoint)
