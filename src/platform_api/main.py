from __future__ import annotations

import json
import logging
import os
from typing import Annotated, Any
from uuid import UUID, uuid4

import uvicorn
from fastapi import Depends, FastAPI, Header, Query, Request, Response, status
from starlette.middleware.base import RequestResponseEndpoint
from strawberry.fastapi import GraphQLRouter

from platform_api import __version__
from platform_api.auth import require_writer_auth
from platform_api.errors import ProblemException, install_exception_handlers
from platform_api.graphql_api import schema
from platform_api.models import (
    WorkItem,
    WorkItemCreate,
    WorkItemPage,
    WorkItemPatch,
    WorkItemPriority,
    WorkItemStatus,
)
from platform_api.repository import (
    IdempotencyConflictError,
    InvalidCursorError,
    ItemNotFoundError,
    VersionConflictError,
    repository,
)

LOGGER = logging.getLogger("platform_api")

PROBLEM_SCHEMA = {
    "type": "object",
    "required": ["type", "title", "status", "detail", "instance", "request_id"],
    "properties": {
        "type": {"type": "string", "format": "uri-reference"},
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "detail": {"type": "string"},
        "instance": {"type": "string", "format": "uri-reference"},
        "request_id": {"type": "string"},
    },
}


def _problem_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    return {
        code: {
            "description": "RFC 9457 problem details",
            "content": {"application/problem+json": {"schema": PROBLEM_SCHEMA}},
        }
        for code in codes
    }


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("MODULE0_LOG_LEVEL", "INFO").upper(),
        format="%(message)s",
    )


def _etag(item: WorkItem) -> str:
    return f'"{item.version}"'


def _parse_if_match(value: str | None) -> int:
    if value is None:
        raise ProblemException(
            status=428,
            title="Precondition required",
            detail="Supply the current ETag in the If-Match header.",
            problem_type="precondition-required",
        )
    try:
        return int(value.strip('"'))
    except ValueError as exc:
        raise ProblemException(
            status=400,
            title="Invalid If-Match header",
            detail="If-Match must contain the numeric ETag returned by the API.",
            problem_type="invalid-precondition",
        ) from exc


def create_app() -> FastAPI:
    app = FastAPI(
        title="Module 0 Platform API",
        summary="A small API for software-engineering foundation labs",
        version=__version__,
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.openapi_version = "3.1.0"
    install_exception_handlers(app)

    @app.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        LOGGER.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                },
                separators=(",", ":"),
            )
        )
        return response

    @app.get("/healthz", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get(
        "/api/v1/work-items",
        response_model=WorkItemPage,
        tags=["work-items"],
        responses=_problem_responses(400, 422),
    )
    async def list_work_items(
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        cursor: str | None = None,
        status_filter: Annotated[WorkItemStatus | None, Query(alias="status")] = None,
        priority: WorkItemPriority | None = None,
        owner: Annotated[str | None, Query(pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")] = None,
    ) -> WorkItemPage:
        try:
            return repository.list(
                limit=limit,
                cursor=cursor,
                status=status_filter,
                priority=priority,
                owner=owner,
            )
        except InvalidCursorError as exc:
            raise ProblemException(
                status=400,
                title="Invalid pagination cursor",
                detail=str(exc),
                problem_type="invalid-cursor",
            ) from exc

    @app.post(
        "/api/v1/work-items",
        response_model=WorkItem,
        status_code=status.HTTP_201_CREATED,
        tags=["work-items"],
        dependencies=[Depends(require_writer_auth)],
        responses=_problem_responses(401, 409, 422, 503),
    )
    async def create_work_item(
        payload: WorkItemCreate,
        response: Response,
        idempotency_key: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=8, max_length=128),
        ],
    ) -> WorkItem:
        try:
            item, replayed = repository.create(payload, idempotency_key)
        except IdempotencyConflictError as exc:
            raise ProblemException(
                status=409,
                title="Idempotency conflict",
                detail=str(exc),
                problem_type="idempotency-conflict",
            ) from exc
        response.headers["Location"] = f"/api/v1/work-items/{item.id}"
        response.headers["ETag"] = _etag(item)
        response.headers["Idempotency-Replayed"] = str(replayed).lower()
        if replayed:
            response.status_code = status.HTTP_200_OK
        return item

    @app.get(
        "/api/v1/work-items/{item_id}",
        response_model=WorkItem,
        tags=["work-items"],
        responses=_problem_responses(404, 422),
    )
    async def get_work_item(item_id: UUID, response: Response) -> WorkItem:
        try:
            item = repository.get(item_id)
        except ItemNotFoundError as exc:
            raise ProblemException(
                status=404,
                title="Work item not found",
                detail=f"No work item exists with id {item_id}.",
                problem_type="not-found",
            ) from exc
        response.headers["ETag"] = _etag(item)
        return item

    @app.patch(
        "/api/v1/work-items/{item_id}",
        response_model=WorkItem,
        tags=["work-items"],
        dependencies=[Depends(require_writer_auth)],
        responses=_problem_responses(400, 401, 404, 412, 422, 428, 503),
    )
    async def update_work_item(
        item_id: UUID,
        patch: WorkItemPatch,
        response: Response,
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> WorkItem:
        expected_version = _parse_if_match(if_match)
        try:
            item = repository.update(item_id, patch, expected_version)
        except ItemNotFoundError as exc:
            raise ProblemException(
                status=404,
                title="Work item not found",
                detail=f"No work item exists with id {item_id}.",
                problem_type="not-found",
            ) from exc
        except VersionConflictError as exc:
            raise ProblemException(
                status=412,
                title="Precondition failed",
                detail="The work item changed after the client last read it.",
                problem_type="precondition-failed",
                extensions={"current_etag": f'"{exc.actual_version}"'},
            ) from exc
        response.headers["ETag"] = _etag(item)
        return item

    app.include_router(GraphQLRouter(schema, graphql_ide="graphiql"), prefix="/graphql")
    return app


app = create_app()


def run() -> None:
    _configure_logging()
    uvicorn.run("platform_api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
