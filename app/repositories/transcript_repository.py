from sqlalchemy.orm import Session

from app.models.transcript import Transcript


class TranscriptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_consultation(self, consultation_id: int) -> Transcript | None:
        return (
            self.db.query(Transcript)
            .filter(Transcript.consultation_id == consultation_id)
            .first()
        )

    def create(
        self,
        consultation_id: int,
        full_text: str,
        raw_response_json: str | None = None,
        cleaned_text: str | None = None,
        role_separated_text: str | None = None,
        cleanup_notes: str | None = None,
    ) -> Transcript:
        transcript = self.get_by_consultation(consultation_id)
        if transcript is None:
            transcript = Transcript(consultation_id=consultation_id, full_text=full_text)
            self.db.add(transcript)

        transcript.full_text = full_text
        transcript.raw_response_json = raw_response_json
        transcript.cleaned_text = cleaned_text
        transcript.role_separated_text = role_separated_text
        transcript.cleanup_notes = cleanup_notes

        self.db.commit()
        self.db.refresh(transcript)

        return transcript
