from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.error_log_class import ErrorLogClass
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

error_logs = APIRouter(
    prefix="/error-logs",
    tags=["Error Logs"],
)


@error_logs.get("/")
def list_error_logs(
    page: int = Query(1, ge=1),
    items_per_page: int = Query(50, ge=1, le=200),
    source: str | None = Query(None),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = ErrorLogClass(db).get_recent(page=page, items_per_page=items_per_page, source=source)
    return {"message": data}
