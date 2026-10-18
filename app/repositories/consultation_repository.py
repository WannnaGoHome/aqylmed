from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.consultation import Consultation, ConsultationSource, ConsultationStatus


class ConsultationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        patient_name: str,
        doctor_name: str,
        consultation_date: str,
        raw_dialogue_text: str,
        *,
        source: str = ConsultationSource.TEXT,
        doctor_id: int | None = None,
        status: str = ConsultationStatus.PROCESSING,
        dialogue_text: str | None = None,
        progress_stage: str | None = "queued",
    ) -> Consultation:
        consultation = Consultation(
            patient_name=patient_name,
            doctor_name=doctor_name,
            consultation_date=consultation_date,
            raw_dialogue_text=raw_dialogue_text,
            dialogue_text=dialogue_text if dialogue_text is not None else raw_dialogue_text or None,
            source=source,
            doctor_id=doctor_id,
            status=status,
            progress_stage=progress_stage,
        )
        self.db.add(consultation)
        self.db.commit()
        self.db.refresh(consultation)

        return consultation

    def get_by_id(self, consultation_id: int) -> Consultation | None:
        return (
            self.db.query(Consultation)
            .filter(Consultation.id == consultation_id)
            .first()
        )

    def list(
        self,
        *,
        doctor_id: int | None = None,
        status: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Consultation], int]:
        q = self.db.query(Consultation)
        if doctor_id is not None:
            q = q.filter(Consultation.doctor_id == doctor_id)
        if status:
            q = q.filter(Consultation.status == status)
        if query:
            like = f"%{query.strip().lower()}%"
            q = q.filter(
                or_(
                    func.lower(Consultation.patient_name).like(like),
                    func.lower(Consultation.doctor_name).like(like),
                )
            )
        total = q.count()
        items = (
            q.order_by(Consultation.created_at.desc(), Consultation.id.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return items, total

    def set_progress(
        self,
        consultation: Consultation,
        *,
        status: str | None = None,
        stage: str | None = None,
        error: str | None = None,
    ) -> Consultation:
        if status is not None:
            consultation.status = status
        consultation.progress_stage = stage
        consultation.error_message = error
        self.db.commit()
        self.db.refresh(consultation)
        return consultation

    def delete(self, consultation: Consultation) -> None:
        self.db.delete(consultation)
        self.db.commit()

    def fail_all_processing(self, message: str) -> int:
        """Вызывается при старте: задачи живут в памяти процесса и после перезапуска потеряны."""
        stuck = (
            self.db.query(Consultation)
            .filter(Consultation.status == ConsultationStatus.PROCESSING)
            .all()
        )
        for consultation in stuck:
            consultation.status = ConsultationStatus.FAILED
            consultation.progress_stage = None
            consultation.error_message = message
        self.db.commit()
        return len(stuck)
