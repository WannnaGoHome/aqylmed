from pydantic import BaseModel


class DialogueProcessingResult(BaseModel):
    cleaned_text: str
    role_separated_text: str
    speaker_roles: dict[str, str] = {}
    uncertain_segments: list[str] = []
    processing_notes: list[str] = []
