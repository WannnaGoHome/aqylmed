from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.usage_record import UsageRecord


class UsageRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, **fields) -> UsageRecord:
        record = UsageRecord(**fields)
        self.db.add(record)
        self.db.commit()
        return record

    def total_cost(self, start: datetime, end: datetime) -> float:
        value = (
            self.db.query(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0))
            .filter(UsageRecord.created_at >= start, UsageRecord.created_at < end)
            .scalar()
        )
        return float(value or 0.0)

    def by_model(self, start: datetime, end: datetime):
        return (
            self.db.query(
                UsageRecord.kind,
                UsageRecord.provider,
                UsageRecord.model,
                func.sum(UsageRecord.cost_usd),
                func.sum(UsageRecord.audio_seconds),
                func.sum(UsageRecord.input_tokens),
                func.sum(UsageRecord.output_tokens),
            )
            .filter(UsageRecord.created_at >= start, UsageRecord.created_at < end)
            .group_by(UsageRecord.kind, UsageRecord.provider, UsageRecord.model)
            .order_by(func.sum(UsageRecord.cost_usd).desc())
            .all()
        )

    def by_day(self, start: datetime, end: datetime):
        day = func.date(UsageRecord.created_at)
        return (
            self.db.query(day, func.sum(UsageRecord.cost_usd))
            .filter(UsageRecord.created_at >= start, UsageRecord.created_at < end)
            .group_by(day)
            .order_by(day)
            .all()
        )

    def consultations_count(self, start: datetime, end: datetime) -> int:
        return (
            self.db.query(func.count(func.distinct(UsageRecord.consultation_id)))
            .filter(
                UsageRecord.created_at >= start,
                UsageRecord.created_at < end,
                UsageRecord.consultation_id.isnot(None),
            )
            .scalar()
            or 0
        )

    def cost_for_consultation(self, consultation_id: int) -> float:
        value = (
            self.db.query(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0))
            .filter(UsageRecord.consultation_id == consultation_id)
            .scalar()
        )
        return float(value or 0.0)
