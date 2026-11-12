from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.config import API_KEY, DASHBOARD_API_KEY

bearer = HTTPBearer(auto_error=False)


def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> bool:
    if (
        creds is None
        or creds.scheme.lower() != "bearer"
        or not secrets.compare_digest(creds.credentials.encode(), API_KEY.encode())
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid API key",
        )
    return True


def require_dashboard_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> bool:
    if creds is not None and creds.scheme.lower() == "bearer":
        if secrets.compare_digest(creds.credentials.encode(), API_KEY.encode()) or (
            DASHBOARD_API_KEY
            and secrets.compare_digest(creds.credentials.encode(), DASHBOARD_API_KEY.encode())
        ):
            return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing or invalid API key",
    )
