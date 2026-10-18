from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, **fields) -> AuditLog:
        entry = AuditLog(**fields)
        self.db.add(entry)
        self.db.commit()
        return entry

    def list(
        self,
        *,
        action: str | None = None,
        user_id: int | None = None,
        entity_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        q = self.db.query(AuditLog)
        if action:
            q = q.filter(AuditLog.action.like(f"{action}%"))
        if user_id is not None:
            q = q.filter(AuditLog.user_id == user_id)
        if entity_id is not None:
            q = q.filter(AuditLog.entity_id == entity_id)
        total = q.count()
        items = q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).offset(offset).all()
        return items, total
