from pydantic import BaseModel

from app.schemas.medical_document import MedicalDocumentDraft
from app.schemas.patient_memo import PatientMemoDraft


class ConsultationAIOutput(BaseModel):
    medical_document: MedicalDocumentDraft
    patient_memo: PatientMemoDraft