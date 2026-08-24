from typing import List, Optional

from app.backend.db.models import EmailLogModel
from datetime import datetime


class EmailLogClass:
    def __init__(self, db):
        self.db = db

    def log_failure(
        self,
        *,
        entity_type: str,
        entity_id: int,
        email_type: str,
        recipient: Optional[str],
        subject: Optional[str],
        error_message: str,
        trigger_source: str,
        cc: Optional[List[str]] = None,
    ) -> None:
        try:
            entry = EmailLogModel(
                entity_type=entity_type,
                entity_id=entity_id,
                email_type=email_type,
                recipient=(recipient or "")[:255],
                cc=(", ".join([e for e in (cc or []) if e]) or None),
                subject=(subject or "")[:255] if subject else None,
                status="failed",
                error_message=str(error_message or "Unknown email error")[:4000],
                trigger_source=trigger_source,
                added_date=datetime.utcnow(),
                updated_date=datetime.utcnow(),
            )
            self.db.add(entry)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            print(f"[EMAIL_LOG] Failed to persist email log: {exc}")

    @staticmethod
    def is_send_success(result: Optional[str]) -> bool:
        text = (result or "").strip().lower()
        return text.startswith("correo enviado")
