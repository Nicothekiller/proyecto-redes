from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid
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
    deleted: Mapped[bool] = mapped_column(default=False, nullable=False)
