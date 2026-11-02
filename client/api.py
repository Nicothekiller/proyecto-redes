from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import requests

from client.config import REQUEST_TIMEOUT_S, SERVER_PORT


class DuplicatePubkeyError(Exception):
    pass


class UnknownNodeError(Exception):
    pass


@dataclass(frozen=True)
class Peer:
    node_id: uuid.UUID
    overlay_ip: str
    pubkey: str
    endpoint: str


@dataclass(frozen=True)
class Registration:
    overlay_ip: str
    peers: list[Peer]


def server_url(server: str) -> str:
    parts = urlsplit(server if "://" in server else f"http://{server}")
    host = parts.hostname
    if host is None:
        raise ValueError(f"invalid server address: {server}")
    return f"{parts.scheme}://{host}:{parts.port or SERVER_PORT}"


def _to_peer(raw: dict[str, Any]) -> Peer:
    return Peer(
        node_id=uuid.UUID(raw["node_id"]),
        overlay_ip=raw["overlay_ip"],
        pubkey=raw["pubkey"],
        endpoint=raw["endpoint"],
    )


class ServerClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {api_key}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        response = self._session.request(
            method, f"{self._base_url}{path}", timeout=REQUEST_TIMEOUT_S, **kwargs
        )
        if response.status_code == 404:
            raise UnknownNodeError(response.json()["detail"])
        if response.status_code == 409:
            raise DuplicatePubkeyError(response.json()["detail"])
        response.raise_for_status()
        return response

    def register(self, node_id: uuid.UUID, pubkey: str, endpoint: str) -> Registration:
        body = self._request(
            "POST",
            "/register",
            json={"node_id": str(node_id), "pubkey": pubkey, "endpoint": endpoint},
        ).json()
        return Registration(
            overlay_ip=body["overlay_ip"],
            peers=[_to_peer(peer) for peer in body["peers"]],
        )
