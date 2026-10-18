import json

from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models.medical_document import MedicalDocument
from app.schemas.medical_document import MedicalDocumentDraft

_TEXT_FIELDS = (
    "complaints", "anamnesis", "symptoms_duration", "examination",
    "diagnosis", "treatment_plan", "recommendations",
)


class MedicalDocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_consultation(self, consultation_id: int) -> MedicalDocument | None:
        return (
            self.db.query(MedicalDocument)
            .filter(MedicalDocument.consultation_id == consultation_id)
            .first()
        )

    def create(
        self,
        consultation_id: int,
        draft: MedicalDocumentDraft,
        warnings: list[str] | None = None,
    ) -> MedicalDocument:
        """Создаёт заключение или полностью заменяет его новым черновиком ИИ (при перегенерации)."""
        document = self.get_by_consultation(consultation_id)
        if document is None:
            document = MedicalDocument(consultation_id=consultation_id)
            self.db.add(document)

        for field in _TEXT_FIELDS:
            setattr(document, field, getattr(draft, field))
        document.missing_information = "\n".join(draft.missing_information)
        document.ai_original_json = draft.model_dump_json()
        document.validation_warnings = json.dumps(warnings or [], ensure_ascii=False)
        document.edited_at = None

        self.db.commit()
        self.db.refresh(document)
        return document

    def update_fields(self, document: MedicalDocument, changes: dict) -> MedicalDocument:
        for field in _TEXT_FIELDS:
            if field in changes and changes[field] is not None:
                setattr(document, field, changes[field])
        if changes.get("missing_information") is not None:
            items = [item.strip() for item in changes["missing_information"] if item.strip()]
            document.missing_information = "\n".join(items)
        document.edited_at = utcnow()
        self.db.commit()
        self.db.refresh(document)
        return document

    def set_warnings(self, document: MedicalDocument, warnings: list[str]) -> None:
        document.validation_warnings = json.dumps(warnings, ensure_ascii=False)
        self.db.commit()
