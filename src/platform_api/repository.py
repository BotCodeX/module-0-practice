from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID, uuid4

from platform_api.models import (
    WorkItem,
    WorkItemCreate,
    WorkItemPage,
    WorkItemPatch,
    WorkItemStatus,
)


class ItemNotFoundError(LookupError):
    pass


class InvalidCursorError(ValueError):
    pass


class IdempotencyConflictError(ValueError):
    pass


class VersionConflictError(ValueError):
    def __init__(self, actual_version: int) -> None:
        super().__init__(f"current version is {actual_version}")
        self.actual_version = actual_version


@dataclass(frozen=True)
class IdempotencyRecord:
    fingerprint: str
    item_id: UUID


def _fingerprint(payload: WorkItemCreate) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _encode_cursor(offset: int) -> str:
    raw = f"work-items:{offset}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        prefix, value = raw.split(":", maxsplit=1)
        if prefix != "work-items":
            raise ValueError
        offset = int(value)
        if offset < 0:
            raise ValueError
        return offset
    except (UnicodeError, ValueError, binascii.Error) as exc:
        raise InvalidCursorError("cursor is invalid or expired") from exc


class InMemoryWorkItemRepository:
    """Thread-safe in-memory repository for labs and tests only."""

    def __init__(self) -> None:
        self._items: dict[UUID, WorkItem] = {}
        self._idempotency: dict[str, IdempotencyRecord] = {}
        self._lock = RLock()

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._idempotency.clear()

    def create(self, payload: WorkItemCreate, idempotency_key: str) -> tuple[WorkItem, bool]:
        fingerprint = _fingerprint(payload)
        with self._lock:
            existing = self._idempotency.get(idempotency_key)
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise IdempotencyConflictError(
                        "the idempotency key was already used with a different request"
                    )
                return self._items[existing.item_id].model_copy(deep=True), True

            item = WorkItem.from_create(uuid4(), payload)
            self._items[item.id] = item
            self._idempotency[idempotency_key] = IdempotencyRecord(fingerprint, item.id)
            return item.model_copy(deep=True), False

    def get(self, item_id: UUID) -> WorkItem:
        with self._lock:
            try:
                return self._items[item_id].model_copy(deep=True)
            except KeyError as exc:
                raise ItemNotFoundError(str(item_id)) from exc

    def list(
        self,
        *,
        limit: int,
        cursor: str | None,
        status: WorkItemStatus | None,
        owner: str | None,
    ) -> WorkItemPage:
        offset = _decode_cursor(cursor)
        with self._lock:
            items = list(self._items.values())
            if status is not None:
                items = [item for item in items if item.status == status]
            if owner is not None:
                items = [item for item in items if item.owner == owner]
            page = items[offset : offset + limit]
            next_offset = offset + limit
            next_cursor = _encode_cursor(next_offset) if next_offset < len(items) else None
            return WorkItemPage(
                items=[item.model_copy(deep=True) for item in page],
                next_cursor=next_cursor,
            )

    def update(self, item_id: UUID, patch: WorkItemPatch, expected_version: int) -> WorkItem:
        with self._lock:
            try:
                current = self._items[item_id]
            except KeyError as exc:
                raise ItemNotFoundError(str(item_id)) from exc
            if current.version != expected_version:
                raise VersionConflictError(current.version)

            changes = patch.model_dump(exclude_unset=True)
            updated = current.model_copy(
                update={
                    **changes,
                    "version": current.version + 1,
                    "updated_at": datetime.now(UTC),
                },
                deep=True,
            )
            self._items[item_id] = updated
            return updated.model_copy(deep=True)


repository = InMemoryWorkItemRepository()
