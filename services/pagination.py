from fastapi import Query, Depends
from typing import Annotated
from dataclasses import dataclass
from sqlalchemy import select, func
from schemas import PaginatedResponse


@dataclass
class PaginationParamsData:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginationParamsData:
    return PaginationParamsData(page=page, page_size=page_size)


PaginationParams = Annotated[PaginationParamsData, Depends(pagination_params)]


async def paginate(db, stmt, params: PaginationParamsData) -> PaginatedResponse:
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.scalar(count_stmt)) or 0

    result = await db.scalars(stmt.limit(params.page_size).offset(params.offset))
    items = result.all()

    total_pages = max((total + params.page_size - 1) // params.page_size, 1)

    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
        has_next=params.page < total_pages,
        has_previous=params.page > 1,
    )
