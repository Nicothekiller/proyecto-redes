from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

from client.config import LISTEN_PORT

STATE_FILE = "state.json"
PRIVATE_KEY_FILE = "privatekey"


@dataclass(frozen=True)
class NodeState:
    node_id: uuid.UUID
    listen_port: int = LISTEN_PORT
    overlay_ip: str | None = None

    def with_overlay_ip(self, overlay_ip: str) -> NodeState:
        return replace(self, overlay_ip=overlay_ip)


def write_private(path: Path, content: str) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(content)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def load_or_create_state(state_dir: Path, listen_port: int = LISTEN_PORT) -> NodeState:
    path = state_dir / STATE_FILE
    if path.is_file():
        raw = json.loads(path.read_text())
        return NodeState(
            node_id=uuid.UUID(raw["node_id"]),
            listen_port=raw["listen_port"],
            overlay_ip=raw["overlay_ip"],
        )
    state = NodeState(node_id=uuid.uuid4(), listen_port=listen_port)
    save_state(state_dir, state)
    return state


def save_state(state_dir: Path, state: NodeState) -> None:
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_private(
        state_dir / STATE_FILE,
        json.dumps(
            {
                "node_id": str(state.node_id),
                "listen_port": state.listen_port,
                "overlay_ip": state.overlay_ip,
            },
            indent=2,
        ),
    )
