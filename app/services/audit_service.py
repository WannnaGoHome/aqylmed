import json

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.audit_repository import AuditRepository


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


class AuditService:
    """Пишет журнал действий. В details попадают только служебные данные (id, имена полей),
    но не содержимое медицинских записей и не ФИО пациентов."""

    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(
        self,
        action: str,
        *,
        user: User | None = None,
        user_email: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        details: dict | None = None,
        request: Request | None = None,
    ) -> None:
        self.repo.add(
            user_id=user.id if user else None,
            user_email=user.email if user else user_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=json.dumps(details, ensure_ascii=False) if details else None,
            ip_address=client_ip(request),
        )
