"""Persistencia de errores de sistema. Nunca debe tumbar el flujo principal."""

from __future__ import annotations

import json
import traceback as tb_module
from datetime import datetime
from typing import Any, Optional

from app.backend.db.database import SessionLocal
from app.backend.db.models import SystemErrorLogModel


class ErrorLogClass:
    @staticmethod
    def _truncate(value: Optional[str], max_len: int = 65000) -> Optional[str]:
        if value is None:
            return None
        text = str(value)
        if len(text) <= max_len:
            return text
        return text[: max_len - 20] + "\n...[truncated]"

    @classmethod
    def log(
        cls,
        message: str,
        *,
        level: str = "error",
        source: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        user_id: Optional[int] = None,
        shopping_id: Optional[int] = None,
        product_id: Optional[int] = None,
        detail: Optional[str] = None,
        request_body: Any = None,
        traceback_text: Optional[str] = None,
        client_ip: Optional[str] = None,
        exc: Optional[BaseException] = None,
    ) -> Optional[int]:
        """Inserta un error en ``system_error_logs``. Devuelve id o None si falla el log."""
        db = SessionLocal()
        try:
            body_text = None
            if request_body is not None:
                if isinstance(request_body, (dict, list)):
                    try:
                        body_text = json.dumps(request_body, ensure_ascii=False, default=str)
                    except Exception:
                        body_text = str(request_body)
                else:
                    body_text = str(request_body)

            if exc is not None and not traceback_text:
                traceback_text = "".join(
                    tb_module.format_exception(type(exc), exc, exc.__traceback__)
                )
            if exc is not None and (not message or message == "error"):
                message = str(exc) or type(exc).__name__

            row = SystemErrorLogModel(
                level=(level or "error")[:20],
                source=(source or None)[:100] if source else None,
                method=(method or None)[:10] if method else None,
                path=(path or None)[:500] if path else None,
                status_code=status_code,
                user_id=user_id,
                shopping_id=shopping_id,
                product_id=product_id,
                message=cls._truncate(message or "Unknown error", 8000) or "Unknown error",
                detail=cls._truncate(detail),
                request_body=cls._truncate(body_text),
                traceback=cls._truncate(traceback_text),
                client_ip=(client_ip or None)[:64] if client_ip else None,
                added_date=datetime.now(),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return int(row.id)
        except Exception as log_error:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"[ErrorLogClass] no se pudo guardar log: {log_error}")
            return None
        finally:
            db.close()

    def get_recent(self, page: int = 1, items_per_page: int = 50, source: Optional[str] = None):
        db = self.db
        query = db.query(SystemErrorLogModel).order_by(SystemErrorLogModel.id.desc())
        if source:
            query = query.filter(SystemErrorLogModel.source == source)

        page = max(int(page or 1), 1)
        items_per_page = min(max(int(items_per_page or 50), 1), 200)
        total = query.count()
        rows = (
            query.offset((page - 1) * items_per_page)
            .limit(items_per_page)
            .all()
        )
        data = [
            {
                "id": r.id,
                "level": r.level,
                "source": r.source,
                "method": r.method,
                "path": r.path,
                "status_code": r.status_code,
                "user_id": r.user_id,
                "shopping_id": r.shopping_id,
                "product_id": r.product_id,
                "message": r.message,
                "detail": r.detail,
                "request_body": r.request_body,
                "traceback": r.traceback,
                "client_ip": r.client_ip,
                "added_date": r.added_date.strftime("%Y-%m-%d %H:%M:%S") if r.added_date else None,
            }
            for r in rows
        ]
        return {
            "status": "success",
            "total_items": total,
            "page": page,
            "items_per_page": items_per_page,
            "data": data,
        }

    def __init__(self, db):
        self.db = db
