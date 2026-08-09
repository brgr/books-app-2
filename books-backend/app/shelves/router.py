from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    PaginatedBooks,
    ShelfBookAdd,
    ShelfItemReorderRequest,
    ShelfNamePayload,
    ShelfResponse,
)
from app.shelves.service import (
    BookNotInLibraryError,
    BuiltInShelfError,
    ShelfNameTakenError,
    ShelfNotFoundError,
    ShelfReorderError,
    ShelfService,
)

router = APIRouter()


async def shelf_error_handler(_request: Request, exception: Exception) -> JSONResponse:
    match exception:
        case ShelfNotFoundError() | BookNotInLibraryError():
            status_code = status.HTTP_404_NOT_FOUND
        case ShelfReorderError() | BuiltInShelfError():
            status_code = status.HTTP_400_BAD_REQUEST
        case ShelfNameTakenError():
            status_code = status.HTTP_409_CONFLICT
        case _:
            raise exception

    return JSONResponse(status_code=status_code, content={"detail": str(exception)})


def get_shelf_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ShelfService:
    return ShelfService(db, current_user)


ShelfServiceDep = Annotated[ShelfService, Depends(get_shelf_service)]


@router.get("/shelves", response_model=list[ShelfResponse])
def list_shelves(service: ShelfServiceDep):
    """Every shelf the user has: the four built-in ones, then their own."""
    return service.list_shelves()


@router.post(
    "/shelves", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED
)
def create_shelf(payload: ShelfNamePayload, service: ShelfServiceDep):
    return service.create_shelf(payload)


@router.patch("/shelves/{ref}", response_model=ShelfResponse)
def update_shelf(ref: str, payload: ShelfNamePayload, service: ShelfServiceDep):
    return service.update_shelf(ref, payload)


@router.delete("/shelves/{ref}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shelf(ref: str, service: ShelfServiceDep):
    service.delete_shelf(ref)
    return None


@router.get("/shelves/{ref}/books", response_model=PaginatedBooks)
def list_books_in_shelf(
    ref: str,
    service: ShelfServiceDep,
    page: int = 1,
    page_size: int = 20,
):
    """Return one page of a shelf's books.

    ``ref`` names a built-in shelf by its ShelfName value or a custom one by id.
    """
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    books, total = service.list_books(service.resolve(ref), page, page_size)

    pages = (total + page_size - 1) // page_size

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post("/shelves/{ref}/books", status_code=status.HTTP_204_NO_CONTENT)
def add_book_to_shelf(ref: str, payload: ShelfBookAdd, service: ShelfServiceDep):
    """Put a book on a custom shelf."""
    service.add_book(ref, payload.book_id)
    return None


@router.delete("/shelves/{ref}/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_book_from_shelf(ref: str, book_id: int, service: ShelfServiceDep):
    service.remove_book(ref, book_id)
    return None


@router.post("/shelves/{ref}/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_shelf_item(
    ref: str,
    payload: ShelfItemReorderRequest,
    service: ShelfServiceDep,
):
    service.reorder(service.resolve(ref), payload)
    return None
