from __future__ import annotations

import ipaddress
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _validate_endpoint(value: str) -> str:
    host, _, port = value.rpartition(":")
    ipaddress.IPv4Address(host)
    if not (port.isascii() and port.isdigit() and 0 < int(port) < 65536):
        raise ValueError("endpoint must be ipv4:port")
    return value


Pubkey = Annotated[str, Field(pattern=r"^[A-Za-z0-9+/]{43}=$")]
Endpoint = Annotated[str, AfterValidator(_validate_endpoint)]


class RegisterIn(BaseModel):
    node_id: uuid.UUID
    pubkey: Pubkey
    endpoint: Endpoint


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
    endpoint: Endpoint | None = None
    probe_ok: bool | None = None
    probe_rtt_ms: float | None = Field(default=None, ge=0)


class HeartbeatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: uuid.UUID
    endpoint: Endpoint | None = None
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
