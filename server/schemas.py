from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class PeerReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    peer_id: uuid.UUID
    last_handshake: int = Field(ge=0)
    rx_bytes: int = Field(ge=0)
    tx_bytes: int = Field(ge=0)
    endpoint: str | None = Field(default=None, min_length=1)
    probe_ok: bool | None = None
    probe_rtt_ms: float | None = Field(default=None, ge=0)


class HeartbeatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: uuid.UUID
    endpoint: str | None = Field(default=None, min_length=1)
    peers: list[PeerReport] = Field(default_factory=list)


class NodeOut(BaseModel):
    node_id: uuid.UUID
    overlay_ip: str
    pubkey: str
    endpoint: str
    last_heartbeat: datetime
    heartbeat_recent: bool
    heartbeat_age_s: float
    connectivity_proven: bool


class PairOut(BaseModel):
    reporter: uuid.UUID
    peer: uuid.UUID
    reporter_overlay_ip: str
    peer_overlay_ip: str
    endpoint: str | None
    last_handshake: int
    handshake_age_s: float | None
    rx_bytes: int
    tx_bytes: int
    probe_ok: bool | None
    probe_rtt_ms: float | None
    probe_ran_at: datetime | None
    connectivity_proven: bool


class StatusOut(BaseModel):
    as_of: datetime
    offline_after_s: int
    probe_ttl_s: int
    nodes_total: int
    pairs: list[PairOut]
