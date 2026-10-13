from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.auth import require_auth
from server.schemas import PeerOut, RegisterIn, RegisterOut
from server.store import get_store
from server.store.base import DuplicatePubkeyError, PoolExhaustedError

router = APIRouter(tags=["nodes"])


@router.post("/register", response_model=RegisterOut)
def register(body: RegisterIn, _auth: bool = Depends(require_auth)) -> RegisterOut:
    store = get_store()
    try:
        overlay_ip, peers = store.register(body.node_id, body.pubkey, body.endpoint)
    except PoolExhaustedError as err:
        raise HTTPException(status_code=503, detail="overlay pool exhausted") from err
    except DuplicatePubkeyError as err:
        raise HTTPException(status_code=409, detail="pubkey already in use") from err
    return RegisterOut(
        overlay_ip=overlay_ip,
        peers=[
            PeerOut(
                node_id=p.node_id,
                overlay_ip=p.overlay_ip,
                pubkey=p.pubkey,
                endpoint=p.endpoint,
            )
            for p in peers
        ],
    )
