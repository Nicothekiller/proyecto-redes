"""M1a: minimal in-memory WireGuard coordination server.

Single process, dicts only, no SQLite yet. Data is lost on restart (expected).

Run:
    API_KEY=<key> uvicorn server.main:app --host 0.0.0.0 --port 8000
    (or put API_KEY=<key> in a .env file at the repo root)
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from server.routers import nodes

app = FastAPI(title="headscale-lite (M1a)")
app.include_router(nodes.router)


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000)
