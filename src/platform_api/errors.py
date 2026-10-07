from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

LOGGER = logging.getLogger("platform_api")
PROBLEM_BASE = "https://module0.example/problems"


class ProblemException(Exception):
    def __init__(
        self,
        *,
        status: int,
        title: str,
        detail: str,
        problem_type: str,
        headers: dict[str, str] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail
        self.problem_type = problem_type
        self.headers = headers or {}
        self.extensions = extensions or {}


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unavailable"))


def _problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    problem_type: str,
    headers: dict[str, str] | None = None,
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{PROBLEM_BASE}/{problem_type}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "request_id": _request_id(request),
    }
    body.update(extensions or {})
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
        headers=headers,
    )


def install_exception_handlers(app: FastAPI) -> None:
    async def handle_problem(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, ProblemException)
        return _problem_response(
            request,
            status=exc.status,
            title=exc.title,
            detail=exc.detail,
            problem_type=exc.problem_type,
            headers=exc.headers,
            extensions=exc.extensions,
        )

    async def handle_validation(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)
        errors = [
            {
                "location": [str(part) for part in error["loc"]],
                "message": error["msg"],
                "code": error["type"],
            }
            for error in exc.errors()
        ]
        return _problem_response(
            request,
            status=422,
            title="Request validation failed",
            detail="One or more request values did not satisfy the API contract.",
            problem_type="validation-error",
            extensions={"errors": errors},
        )

    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception("unhandled request failure", extra={"request_id": _request_id(request)})
        return _problem_response(
            request,
            status=500,
            title="Internal server error",
            detail="The service could not complete the request.",
            problem_type="internal-error",
        )

    app.add_exception_handler(ProblemException, handle_problem)
    app.add_exception_handler(RequestValidationError, handle_validation)
    app.add_exception_handler(Exception, handle_unexpected)
