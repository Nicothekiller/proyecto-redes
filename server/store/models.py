from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    node_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    pubkey: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    overlay_ip: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PeerStatus(Base):
    __tablename__ = "peer_status"

    reporter_node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        primary_key=True,
    )
    peer_node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("nodes.node_id", ondelete="CASCADE"),
        primary_key=True,
    )
    endpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    last_handshake: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rx_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tx_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    probe_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    probe_rtt_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    probe_ran_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
