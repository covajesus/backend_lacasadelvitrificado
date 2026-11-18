from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.error_log_class import ErrorLogClass
from app.backend.db.database import get_db
from app.backend.schemas import UserLogin

error_logs = APIRouter(
    prefix="/error-logs",
    tags=["Error Logs"],
)


class ClientErrorLogInput(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    detail: Optional[str] = None
    path: Optional[str] = None
    source: Optional[str] = "frontend"
    stack: Optional[str] = None
    extra: Optional[Any] = None


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


@error_logs.post("/client")
def store_client_error(payload: ClientErrorLogInput, request: Request):
    """Recibe errores del frontend (Vue/axios) para ver fallos de toda la app."""
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    log_id = ErrorLogClass.log(
        message=payload.message,
        level="error",
        source=(payload.source or "frontend")[:100],
        method="CLIENT",
        path=(payload.path or "")[:500] or None,
        status_code=None,
        detail=payload.detail,
        request_body=payload.extra,
        traceback_text=payload.stack,
        client_ip=client_ip,
    )
    return {"message": {"status": "success", "id": log_id}}
