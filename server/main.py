"""M1a: minimal in-memory WireGuard coordination server.

Single process, dicts only, no SQLite yet. Data is lost on restart (expected).

Run:
    API_KEY=<key> uvicorn server.main:app --host 0.0.0.0 --port 8000
    (or put API_KEY=<key> in a .env file at the repo root)
"""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from server.routers import nodes
from server.store.base import (
    DuplicatePubkeyError,
    PoolExhaustedError,
    UnknownNodeError,
)

app = FastAPI(title="headscale-lite (M1a)")
app.include_router(nodes.router)


def _error(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.exception_handler(UnknownNodeError)
def _unknown_node(request: Request, exc: UnknownNodeError) -> JSONResponse:
    return _error(404, "unknown node")


@app.exception_handler(PoolExhaustedError)
def _pool_exhausted(request: Request, exc: PoolExhaustedError) -> JSONResponse:
    return _error(503, "overlay pool exhausted")


@app.exception_handler(DuplicatePubkeyError)
def _duplicate_pubkey(request: Request, exc: DuplicatePubkeyError) -> JSONResponse:
    return _error(409, "pubkey already in use")


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000)
