from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

OWNER_PATTERN = r"^[a-z0-9][a-z0-9-]{1,62}$"
LABEL_PATTERN = r"^[a-z0-9][a-z0-9-]{0,31}$"


class WorkItemStatus(StrEnum):
    BACKLOG = "backlog"
    READY = "ready"
    DOING = "doing"
    DONE = "done"


class WorkItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    owner: str = Field(pattern=OWNER_PATTERN)
    status: WorkItemStatus = WorkItemStatus.BACKLOG
    labels: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, labels: list[str]) -> list[str]:
        cleaned = [label.strip().lower() for label in labels]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("labels must be unique")
        import re

        invalid = [label for label in cleaned if re.fullmatch(LABEL_PATTERN, label) is None]
        if invalid:
            raise ValueError("labels must contain lowercase letters, numbers or hyphens")
        return cleaned


class WorkItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    owner: str | None = Field(default=None, pattern=OWNER_PATTERN)
    status: WorkItemStatus | None = None
    labels: list[str] | None = Field(default=None, max_length=8)

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, labels: list[str] | None) -> list[str] | None:
        if labels is None:
            return None
        return WorkItemCreate.validate_labels(labels)

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class WorkItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    title: str
    description: str | None
    owner: str
    status: WorkItemStatus
    labels: list[str]
    version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_create(cls, item_id: UUID, payload: WorkItemCreate) -> WorkItem:
        now = datetime.now(UTC)
        return cls(
            id=item_id,
            version=1,
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )


class WorkItemPage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[WorkItem]
    next_cursor: str | None


class WorkItemFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[WorkItemCreate] = Field(min_length=1, max_length=20)


class ProblemDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str
