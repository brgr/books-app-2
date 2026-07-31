from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models import ShelfName, User
from app.schemas import PaginatedBooks, ShelfItemReorderRequest
from app.shelves.service import (
    BookNotInLibraryError,
    ShelfReorderError,
    ShelfService,
)

router = APIRouter()


def get_shelf_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ShelfService:
    return ShelfService(db, current_user)


@router.get("/shelves/{shelf_name}/books", response_model=PaginatedBooks)
def list_books_in_shelf(
    shelf_name: ShelfName,
    service: Annotated[ShelfService, Depends(get_shelf_service)],
    page: int = 1,
    page_size: int = 20,
):
    """Return one page of a built-in shelf's books.

    ``shelf_name`` is the ShelfName enum, so anything outside the four built-in shelves is
    rejected with a 422 before this runs.

     Note that that is on purpose. We might add something like user-created collections /
     shelves at one point, but we will have to figure out the API semantics then.
    """
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    books, total = service.list_books(shelf_name, page, page_size)

    pages = (total + page_size - 1) // page_size

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post(
    "/shelves/{shelf_name}/items/reorder", status_code=status.HTTP_204_NO_CONTENT
)
def reorder_shelf_item(
    shelf_name: ShelfName,
    payload: ShelfItemReorderRequest,
    service: Annotated[ShelfService, Depends(get_shelf_service)],
):
    try:
        service.reorder(shelf_name, payload)
    except BookNotInLibraryError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ShelfReorderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return None
