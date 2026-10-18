"""Запуск обработки в фоне со своей сессией БД. Ограничивает число одновременных тяжёлых задач.

Задачи живут в памяти процесса: для пилота на одном сервере этого достаточно; при росте нагрузки
этот класс заменяется очередью (RQ/Celery) без изменений в API.
"""
import threading
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.consultation_service import ConsultationService


class ProcessingRunner:
    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
        service_factory: Callable[[Session], ConsultationService] | None = None,
    ):
        self.session_factory = session_factory
        self.service_factory = service_factory or (lambda db: ConsultationService(db))
        self._semaphore = threading.BoundedSemaphore(max(1, settings.max_concurrent_processing))

    def run(self, consultation_id: int, mode: str) -> None:
        with self._semaphore:
            with self.session_factory() as db:
                service = self.service_factory(db)
                if mode == "text":
                    service.run_text_processing(consultation_id)
                elif mode == "audio":
                    service.run_audio_processing(consultation_id)
                else:
                    service.regenerate(consultation_id)


_runner: ProcessingRunner | None = None


def get_runner() -> ProcessingRunner:
    global _runner
    if _runner is None:
        _runner = ProcessingRunner()
    return _runner
