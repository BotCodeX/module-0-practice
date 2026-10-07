from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from platform_api.errors import ProblemException

bearer = HTTPBearer(auto_error=False)


def require_writer_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    expected = os.getenv("MODULE0_API_TOKEN")
    if not expected:
        raise ProblemException(
            status=503,
            title="Write authentication is not configured",
            detail="The service administrator must configure MODULE0_API_TOKEN.",
            problem_type="configuration-error",
        )
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not secrets.compare_digest(credentials.credentials, expected)
    ):
        raise ProblemException(
            status=401,
            title="Authentication required",
            detail="Supply a valid bearer token for this write operation.",
            problem_type="authentication-required",
            headers={"WWW-Authenticate": "Bearer"},
        )
