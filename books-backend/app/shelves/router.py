from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    PaginatedBooks,
    CustomShelfBookAdd,
    ShelfReorderRequest,
    CustomShelfNamePayload,
    ShelfResponse,
)
from app.shelves.service import (
    BookNotInLibraryError,
    ReadingShelfError,
    CustomShelfNameTakenError,
    ShelfNotFoundError,
    ShelfReorderError,
    ShelfService,
)
from app.shelves.refs import InvalidShelfRefError, ShelfRef, parse_shelf_ref

router = APIRouter()


async def shelf_error_handler(_request: Request, exception: Exception) -> JSONResponse:
    match exception:
        case ShelfNotFoundError() | BookNotInLibraryError():
            status_code = status.HTTP_404_NOT_FOUND
        case ShelfReorderError() | ReadingShelfError():
            status_code = status.HTTP_400_BAD_REQUEST
        case CustomShelfNameTakenError():
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


def get_shelf_ref(ref: str) -> ShelfRef:
    """Parse the route's shelf ref before it reaches the service layer."""
    try:
        return parse_shelf_ref(ref)
    except InvalidShelfRefError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from None


ShelfRefDep = Annotated[ShelfRef, Depends(get_shelf_ref)]


@router.get("/shelves", response_model=list[ShelfResponse])
def list_shelves(service: ShelfServiceDep):
    """Every shelf the user has: the four reading shelves, then their custom ones."""
    return service.list_shelves()


@router.get("/books/{book_id}/custom-shelves", response_model=list[ShelfResponse])
def list_book_custom_shelves(book_id: int, service: ShelfServiceDep):
    """The custom shelves containing a library book."""
    return service.list_book_custom_shelves(book_id)


@router.post(
    "/shelves", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED
)
def create_shelf(payload: CustomShelfNamePayload, service: ShelfServiceDep):
    return service.create_shelf(payload)


@router.patch("/shelves/{ref}", response_model=ShelfResponse)
def update_shelf(
    shelf_ref: ShelfRefDep,
    payload: CustomShelfNamePayload,
    service: ShelfServiceDep,
):
    return service.update_shelf(shelf_ref, payload)


@router.delete("/shelves/{ref}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shelf(shelf_ref: ShelfRefDep, service: ShelfServiceDep):
    service.delete_shelf(shelf_ref)
    return None


@router.get("/shelves/{ref}/books", response_model=PaginatedBooks)
def list_books_in_shelf(
    shelf_ref: ShelfRefDep,
    service: ShelfServiceDep,
    page: int = 1,
    page_size: int = 20,
):
    """Return one page of a shelf's books.

    ``ref`` names a shelf as ``reading:<ReadingShelf value>`` or ``custom:<id>``.
    """
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 20

    books, total = service.list_books(service.resolve(shelf_ref), page, page_size)

    pages = (total + page_size - 1) // page_size

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post("/shelves/{ref}/books", status_code=status.HTTP_204_NO_CONTENT)
def add_book_to_shelf(
    shelf_ref: ShelfRefDep,
    payload: CustomShelfBookAdd,
    service: ShelfServiceDep,
):
    """Put a book on a custom shelf."""
    service.add_book(shelf_ref, payload.book_id)
    return None


@router.delete("/shelves/{ref}/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_book_from_shelf(
    shelf_ref: ShelfRefDep, book_id: int, service: ShelfServiceDep
):
    service.remove_book(shelf_ref, book_id)
    return None


@router.post("/shelves/{ref}/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_shelf_item(
    shelf_ref: ShelfRefDep,
    payload: ShelfReorderRequest,
    service: ShelfServiceDep,
):
    service.reorder(service.resolve(shelf_ref), payload)
    return None
