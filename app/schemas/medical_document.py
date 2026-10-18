from pydantic import BaseModel, field_validator


class MedicalDocumentDraft(BaseModel):
    """Черновик заключения от ИИ. Допускаем пропущенные/null-поля: модель иногда их не возвращает."""

    complaints: str = ""
    anamnesis: str = ""
    symptoms_duration: str = ""
    examination: str = ""
    diagnosis: str = ""
    treatment_plan: str = ""
    recommendations: str = ""
    missing_information: list[str] = []

    @field_validator(
        "complaints", "anamnesis", "symptoms_duration", "examination",
        "diagnosis", "treatment_plan", "recommendations",
        mode="before",
    )
    @classmethod
    def _none_to_empty(cls, value):
        return "" if value is None else value

    @field_validator("missing_information", mode="before")
    @classmethod
    def _normalize_missing(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return value
