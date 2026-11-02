from __future__ import annotations

from uuid import uuid4

import pytest

from platform_api.models import WorkItemCreate, WorkItemPatch, WorkItemPriority, WorkItemStatus
from platform_api.repository import (
    IdempotencyConflictError,
    InMemoryWorkItemRepository,
    InvalidCursorError,
    ItemNotFoundError,
    VersionConflictError,
)

pytestmark = pytest.mark.unit


def payload(title: str = "Write the contract") -> WorkItemCreate:
    return WorkItemCreate(title=title, owner="platform-team", status=WorkItemStatus.READY)


def test_create_replays_the_same_logical_operation() -> None:
    repo = InMemoryWorkItemRepository()
    first, replayed = repo.create(payload(), "same-operation")
    second, second_replayed = repo.create(payload(), "same-operation")
    assert replayed is False
    assert second_replayed is True
    assert first.id == second.id


def test_idempotency_key_cannot_be_reused_for_different_input() -> None:
    repo = InMemoryWorkItemRepository()
    repo.create(payload(), "same-operation")
    with pytest.raises(IdempotencyConflictError):
        repo.create(payload("Different work"), "same-operation")


def test_update_requires_the_current_version() -> None:
    repo = InMemoryWorkItemRepository()
    item, _ = repo.create(payload(), "operation-one")
    updated = repo.update(item.id, WorkItemPatch(status=WorkItemStatus.DONE), expected_version=1)
    assert updated.version == 2
    assert updated.status == WorkItemStatus.DONE
    with pytest.raises(VersionConflictError):
        repo.update(item.id, WorkItemPatch(status=WorkItemStatus.READY), expected_version=1)


def test_invalid_cursor_and_unknown_item_are_distinct() -> None:
    repo = InMemoryWorkItemRepository()
    with pytest.raises(InvalidCursorError):
        repo.list(limit=10, cursor="not-a-cursor", status=None, owner=None)
    with pytest.raises(ItemNotFoundError):
        repo.get(uuid4())


def test_pagination_and_filters_are_applied_in_repository_order() -> None:
    repo = InMemoryWorkItemRepository()
    first, _ = repo.create(payload("First item"), "operation-one")
    second, _ = repo.create(payload("Second item"), "operation-two")
    repo.create(
        WorkItemCreate(title="Backlog item", owner="other-team"),
        "operation-three",
    )
    first_page = repo.list(limit=1, cursor=None, status=WorkItemStatus.READY, owner=None)
    assert [item.id for item in first_page.items] == [first.id]
    assert first_page.next_cursor is not None
    second_page = repo.list(
        limit=1,
        cursor=first_page.next_cursor,
        status=WorkItemStatus.READY,
        owner=None,
    )
    assert [item.id for item in second_page.items] == [second.id]
    owner_page = repo.list(limit=10, cursor=None, status=None, owner="other-team")
    assert [item.owner for item in owner_page.items] == ["other-team"]


def test_status_and_owner_filters_must_both_match() -> None:
    repo = InMemoryWorkItemRepository()

    matching, _ = repo.create(
        WorkItemCreate(
            title="Matching item",
            owner="platform-team",
            status=WorkItemStatus.READY,
        ),
        "filter-operation-1",
    )
    repo.create(
        WorkItemCreate(
            title="Wrong owner",
            owner="other-team",
            status=WorkItemStatus.READY,
        ),
        "filter-operation-2",
    )
    repo.create(
        WorkItemCreate(
            title="Wrong status",
            owner="platform-team",
            status=WorkItemStatus.DOING,
        ),
        "filter-operation-3",
    )

    result = repo.list(
        limit=10,
        cursor=None,
        status=WorkItemStatus.READY,
        owner="platform-team",
    )

    assert [item.id for item in result.items] == [matching.id]


def test_update_of_unknown_item_fails() -> None:
    repo = InMemoryWorkItemRepository()
    with pytest.raises(ItemNotFoundError):
        repo.update(uuid4(), WorkItemPatch(status=WorkItemStatus.DONE), expected_version=1)


def test_priority_filter_returns_only_matching_items() -> None:
    repo = InMemoryWorkItemRepository()

    high_item, _ = repo.create(
        WorkItemCreate(
            title="High priority task",
            owner="platform-team",
            priority=WorkItemPriority.HIGH,
        ),
        "priority-operation-1",
    )

    repo.create(
        WorkItemCreate(
            title="Low priority task",
            owner="platform-team",
            priority=WorkItemPriority.LOW,
        ),
        "priority-operation-2",
    )

    result = repo.list(
        limit=10,
        cursor=None,
        status=None,
        owner=None,
        priority=WorkItemPriority.HIGH,
    )

    assert [item.id for item in result.items] == [high_item.id]
