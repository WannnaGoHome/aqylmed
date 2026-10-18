from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models.patient_memo import PatientMemo
from app.schemas.patient_memo import PatientMemoDraft


class PatientMemoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_consultation(self, consultation_id: int) -> PatientMemo | None:
        return (
            self.db.query(PatientMemo)
            .filter(PatientMemo.consultation_id == consultation_id)
            .first()
        )

    def create(
        self,
        consultation_id: int,
        draft: PatientMemoDraft,
    ) -> PatientMemo:
        memo = self.get_by_consultation(consultation_id)
        if memo is None:
            memo = PatientMemo(consultation_id=consultation_id, memo_text=draft.memo_text)
            self.db.add(memo)
        memo.memo_text = draft.memo_text
        memo.ai_original_text = draft.memo_text
        memo.edited_at = None

        self.db.commit()
        self.db.refresh(memo)
        return memo

    def update_text(self, memo: PatientMemo, text: str) -> PatientMemo:
        memo.memo_text = text
        memo.edited_at = utcnow()
        self.db.commit()
        self.db.refresh(memo)
        return memo
