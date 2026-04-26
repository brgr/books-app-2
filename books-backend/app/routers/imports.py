from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Import, User
from app.reading_list_import import (
    ImportReadingListError,
    import_reading_list_from_bytes,
)
from app.schemas import ImportResponse

router = APIRouter()


@router.post("/import/reading-list")
def import_reading_list(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        return import_reading_list_from_bytes(
            db,
            cast(int, current_user.id),
            file.file.read(),
            filename=file.filename,
        )
    except ImportReadingListError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/imports", response_model=list[ImportResponse])
def list_imports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return (
        db.query(Import)
        .filter(Import.user_id == current_user.id)
        .order_by(Import.occurred_at.desc())
        .all()
    )
