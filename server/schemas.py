from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    node_id: uuid.UUID
    pubkey: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)


class PeerOut(BaseModel):
    node_id: uuid.UUID
    overlay_ip: str
    pubkey: str
    endpoint: str


class RegisterOut(BaseModel):
    overlay_ip: str
    peers: list[PeerOut]


class HeartbeatIn(BaseModel):
    node_id: uuid.UUID
    endpoint: str | None = Field(default=None, min_length=1)
