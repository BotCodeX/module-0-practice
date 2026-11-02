from __future__ import annotations

from uuid import UUID

import strawberry

from platform_api.models import WorkItem, WorkItemPriority, WorkItemStatus
from platform_api.repository import ItemNotFoundError, repository


@strawberry.type
class GraphQLWorkItem:
    id: strawberry.ID
    title: str
    description: str | None
    owner: str
    status: str
    priority: str
    labels: list[str]
    version: int

    @classmethod
    def from_model(cls, item: WorkItem) -> GraphQLWorkItem:
        return cls(
            id=strawberry.ID(str(item.id)),
            title=item.title,
            description=item.description,
            owner=item.owner,
            status=item.status.value,
            priority=item.priority.value,
            labels=item.labels,
            version=item.version,
        )


@strawberry.type
class Query:
    @strawberry.field
    async def work_item(self, id: strawberry.ID) -> GraphQLWorkItem | None:
        try:
            item = repository.get(UUID(str(id)))
        except (ItemNotFoundError, ValueError):
            return None
        return GraphQLWorkItem.from_model(item)

    @strawberry.field
    async def work_items(
        self, limit: int = 20, status: str | None = None, priority: str | None = None
    ) -> list[GraphQLWorkItem]:
        bounded_limit = min(max(limit, 1), 100)
        parsed_status = WorkItemStatus(status) if status is not None else None
        parsed_priority = WorkItemPriority(priority) if priority is not None else None
        page = repository.list(
            limit=bounded_limit,
            cursor=None,
            status=parsed_status,
            priority=parsed_priority,
            owner=None,
        )
        return [GraphQLWorkItem.from_model(item) for item in page.items]


schema = strawberry.Schema(query=Query)
