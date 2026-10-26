from pydantic import BaseModel
from typing import Literal

from app.schemas.medical_document import MedicalDocumentDraft
from app.schemas.patient_memo import PatientMemoDraft


class ConsultationAIOutput(BaseModel):
    output_locale: Literal["ru", "kk", "en"] | None = None
    medical_document: MedicalDocumentDraft
    patient_memo: PatientMemoDraft