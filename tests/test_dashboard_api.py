from __future__ import annotations

import time
import uuid

from fastapi.testclient import TestClient

A = uuid.UUID("11111111-1111-1111-1111-111111111111")
B = uuid.UUID("22222222-2222-2222-2222-222222222222")

AUTH = {"Authorization": "Bearer testkey"}


def _register(client: TestClient, node_id: uuid.UUID, pubkey: str, endpoint: str) -> None:
    response = client.post(
        "/register",
        json={"node_id": str(node_id), "pubkey": pubkey, "endpoint": endpoint},
        headers=AUTH,
    )
    assert response.status_code == 200


def _heartbeat_probe(client: TestClient) -> None:
    response = client.post(
        "/heartbeat",
        json={
            "node_id": str(A),
            "endpoint": "10.0.0.1:51820",
            "peers": [
                {
                    "peer_id": str(B),
                    "last_handshake": int(time.time()),
                    "rx_bytes": 100,
                    "tx_bytes": 200,
                    "probe_ok": True,
                    "probe_rtt_ms": 1.5,
                }
            ],
        },
        headers=AUTH,
    )
    assert response.status_code == 204


def test_nodes_exposes_heartbeat_and_connectivity(client: TestClient) -> None:
    _register(client, A, "pubA", "10.0.0.1:51820")
    _register(client, B, "pubB", "10.0.0.2:51820")
    _heartbeat_probe(client)

    response = client.get("/nodes", headers=AUTH)
    assert response.status_code == 200
    nodes = {node["node_id"]: node for node in response.json()}

    node_a = nodes[str(A)]
    assert node_a["heartbeat_recent"] is True
    assert node_a["heartbeat_age_s"] >= 0
    assert node_a["connectivity_proven"] is True
    assert node_a["pubkey"] == "pubA"
    assert "peer_count" not in node_a

    assert nodes[str(B)]["connectivity_proven"] is True


def test_status_reports_directed_pairs(client: TestClient) -> None:
    _register(client, A, "pubA", "10.0.0.1:51820")
    _register(client, B, "pubB", "10.0.0.2:51820")
    _heartbeat_probe(client)

    response = client.get("/status", headers=AUTH)
    assert response.status_code == 200
    body = response.json()

    assert body["offline_after_s"] == 30
    assert body["probe_ttl_s"] == 15
    assert body["nodes_total"] == 2
    assert body["as_of"]

    pair = body["pairs"][0]
    assert pair["reporter"] == str(A)
    assert pair["peer"] == str(B)
    assert pair["reporter_overlay_ip"] == "10.100.0.2"
    assert pair["peer_overlay_ip"] == "10.100.0.3"
    assert pair["handshake_age_s"] is not None
    assert pair["connectivity_proven"] is True
    assert pair["probe_ran_at"] is not None


def test_status_without_reports_is_empty(client: TestClient) -> None:
    _register(client, A, "pubA", "10.0.0.1:51820")

    body = client.get("/status", headers=AUTH).json()
    assert body["nodes_total"] == 1
    assert body["pairs"] == []


def test_dashboard_requires_auth(client: TestClient) -> None:
    assert client.get("/nodes").status_code == 401
    assert client.get("/status").status_code == 401
    assert client.get("/nodes", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_heartbeat_rejects_unknown_fields(client: TestClient) -> None:
    _register(client, A, "pubA", "10.0.0.1:51820")

    response = client.post(
        "/heartbeat",
        json={"node_id": str(A), "private_key": "leak"},
        headers=AUTH,
    )
    assert response.status_code == 422


def test_responses_contain_no_secrets(client: TestClient) -> None:
    _register(client, A, "pubA", "10.0.0.1:51820")
    _register(client, B, "pubB", "10.0.0.2:51820")
    _heartbeat_probe(client)

    for path in ("/nodes", "/status"):
        text = client.get(path, headers=AUTH).text.lower()
        assert "private" not in text
        assert "preshared" not in text
