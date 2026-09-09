"""Authentication boundary for protected NGDP API routes."""

from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

API_TOKEN_ENV_VAR = "NGDP_API_TOKEN"
MINIMUM_TOKEN_LENGTH = 32

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="NGDP bearer token",
    description="Service token configured through the NGDP_API_TOKEN environment variable.",
)


def require_api_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> None:
    """Require the configured bearer token without exposing its value."""

    configured_token = os.environ.get(API_TOKEN_ENV_VAR, "").strip()
    if len(configured_token) < MINIMUM_TOKEN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    supplied_token = credentials.credentials if credentials else ""
    if not secrets.compare_digest(supplied_token, configured_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
