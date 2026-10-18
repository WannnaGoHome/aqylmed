import logging
from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutils import utcnow
from app.models.audio_file import AudioFile
from app.repositories.audio_file_repository import AudioFileRepository

logger = logging.getLogger(__name__)


class AudioRetentionService:
    def __init__(self, db: Session):
        self.repo = AudioFileRepository(db)

    def delete_audio(self, audio: AudioFile) -> bool:
        """Удаляет файл с диска и помечает запись удалённой. Возвращает True, если файл существовал."""
        existed = False
        path = Path(audio.file_path)
        try:
            if path.exists():
                path.unlink()
                existed = True
        except OSError:
            logger.exception("Не удалось удалить аудиофайл %s", audio.id)
            raise
        self.repo.mark_deleted(audio)
        return existed

    def purge_expired(self) -> int:
        days = settings.audio_retention_days
        if days <= 0:
            return 0
        expired = self.repo.list_expired(utcnow() - timedelta(days=days))
        for audio in expired:
            self.delete_audio(audio)
        if expired:
            logger.info("Retention: удалено аудиозаписей: %d", len(expired))
        return len(expired)
