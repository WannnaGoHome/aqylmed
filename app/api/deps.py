import threading
import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token, credential_fingerprint
import hmac
from app.models.consultation import Consultation
from app.models.user import User, UserRole
from app.repositories.consultation_repository import ConsultationRepository
from app.repositories.user_repository import UserRepository
from app.services.runner import ProcessingRunner, get_runner as _get_runner

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Требуется вход в систему", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthorized
    payload = decode_access_token(credentials.credentials)
    if not payload or not str(payload.get("sub", "")).isdigit():
        raise unauthorized
    user = UserRepository(db).get_by_id(int(payload["sub"]))
    if (user is None or not user.is_active or not user.email_verified
            or not hmac.compare_digest(str(payload.get("credential", "")), credential_fingerprint(user.hashed_password))):
        raise unauthorized
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Доступно только администратору")
    return user


def get_runner() -> ProcessingRunner:
    return _get_runner()


def get_consultation_or_404(db: Session, consultation_id: int, user: User) -> Consultation:
    """Врач видит только свои приёмы, администратор — все. Чужой приём = 404, чтобы не раскрывать его существование."""
    consultation = ConsultationRepository(db).get_by_id(consultation_id)
    if consultation is None or (user.role != UserRole.ADMIN and consultation.doctor_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Приём не найден")
    return consultation


class LoginLimiter:
    """Блокировка перебора пароля: N неудачных попыток -> пауза. Состояние в памяти процесса."""

    def __init__(self):
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        window = settings.login_lockout_minutes * 60
        now = time.monotonic()
        recent = [t for t in self._failures.get(key, []) if now - t < window]
        self._failures[key] = recent
        return recent

    def is_locked(self, key: str) -> bool:
        with self._lock:
            return len(self._recent(key)) >= settings.login_max_attempts

    def register_failure(self, key: str) -> None:
        with self._lock:
            self._recent(key).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_limiter = LoginLimiter()


def request_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
