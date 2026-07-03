from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.book_list_service import (
    BookListService,
    BookNotInLibraryError,
    ListNotFoundError,
    ListReorderError,
)
from app.database import get_db
from app.models import User
from app.schemas import BookListItemReorderRequest, BookListResponse, PaginatedBooks

router = APIRouter()


def get_book_list_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BookListService:
    return BookListService(db, current_user)


@router.get("/lists", response_model=list[BookListResponse])
def list_book_lists(
    service: Annotated[BookListService, Depends(get_book_list_service)],
):
    return service.get_lists()


@router.get("/lists/{list_id}/books", response_model=PaginatedBooks)
def list_books_in_list(
    list_id: int,
    service: Annotated[BookListService, Depends(get_book_list_service)],
    page: int = 1,
    page_size: int = 20,
):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    try:
        books, total = service.list_books(list_id, page, page_size)
    except ListNotFoundError as exc:
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


@router.post("/lists/{list_id}/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_list_item(
    list_id: int,
    payload: BookListItemReorderRequest,
    service: Annotated[BookListService, Depends(get_book_list_service)],
):
    try:
        service.reorder(list_id, payload)
    except (ListNotFoundError, BookNotInLibraryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ListReorderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return None
