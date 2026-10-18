from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models.audio_file import AudioFile


class AudioFileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_consultation(self, consultation_id: int) -> AudioFile | None:
        return (
            self.db.query(AudioFile)
            .filter(AudioFile.consultation_id == consultation_id)
            .first()
        )

    def create(
        self,
        consultation_id: int,
        file_path: str,
        duration_seconds: int | None = None,
    ) -> AudioFile:
        file_format = Path(file_path).suffix.replace(".", "").lower()

        audio_file = self.get_by_consultation(consultation_id)
        if audio_file is None:
            audio_file = AudioFile(
                consultation_id=consultation_id,
                file_path=file_path,
                file_format=file_format,
            )
            self.db.add(audio_file)
        audio_file.file_path = file_path
        audio_file.file_format = file_format
        audio_file.duration_seconds = duration_seconds
        audio_file.is_deleted = False
        audio_file.deleted_at = None

        self.db.commit()
        self.db.refresh(audio_file)

        return audio_file

    def set_duration(self, audio_file: AudioFile, duration_seconds: int) -> None:
        audio_file.duration_seconds = duration_seconds
        self.db.commit()

    def mark_deleted(self, audio_file: AudioFile) -> None:
        audio_file.is_deleted = True
        audio_file.deleted_at = utcnow()
        self.db.commit()

    def list_expired(self, older_than: datetime) -> list[AudioFile]:
        return (
            self.db.query(AudioFile)
            .filter(AudioFile.is_deleted.is_(False), AudioFile.created_at < older_than)
            .all()
        )
