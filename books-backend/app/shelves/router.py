from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import PaginatedBooks, ShelfItemReorderRequest, ShelfResponse
from app.shelves.service import (
    BookNotInLibraryError,
    ShelfNotFoundError,
    ShelfReorderError,
    ShelfService,
)

router = APIRouter()


def get_shelf_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ShelfService:
    return ShelfService(db, current_user)


@router.get("/shelves", response_model=list[ShelfResponse])
def list_shelves(
    service: Annotated[ShelfService, Depends(get_shelf_service)],
):
    return service.get_shelves()


@router.get("/shelves/{shelf_id}/books", response_model=PaginatedBooks)
def list_books_in_shelf(
    shelf_id: int,
    service: Annotated[ShelfService, Depends(get_shelf_service)],
    page: int = 1,
    page_size: int = 20,
):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    try:
        books, total = service.list_books(shelf_id, page, page_size)
    except ShelfNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    pages = (total + page_size - 1) // page_size

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post(
    "/shelves/{shelf_id}/items/reorder", status_code=status.HTTP_204_NO_CONTENT
)
def reorder_shelf_item(
    shelf_id: int,
    payload: ShelfItemReorderRequest,
    service: Annotated[ShelfService, Depends(get_shelf_service)],
):
    try:
        service.reorder(shelf_id, payload)
    except (ShelfNotFoundError, BookNotInLibraryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ShelfReorderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return None
