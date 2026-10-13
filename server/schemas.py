from __future__ import annotations

from pydantic import BaseModel


class RegisterIn(BaseModel):
    node_id: str
    pubkey: str
    endpoint: str


class PeerOut(BaseModel):
    node_id: str
    overlay_ip: str
    pubkey: str
    endpoint: str


class RegisterOut(BaseModel):
    overlay_ip: str
    peers: list[PeerOut]
