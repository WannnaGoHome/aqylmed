import logging
import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, login_limiter, request_ip
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token, hash_password, validate_password_strength, verify_password,
)
from app.core.timeutils import utcnow
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.api import (
    ChangePasswordRequest, LoginRequest, PasswordResetConfirm, PasswordResetRequest,
    TokenResponse, UserOut, VerifyLoginCodeRequest,
    UserPreferencesUpdate,
)
from app.services.audit_service import AuditService
from app.services.email_service import EmailDeliveryError, send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

_BAD_CREDENTIALS = "Неверный email или пароль"
_GENERIC_RESET = "Если адрес зарегистрирован, на него отправлена ссылка для сброса пароля"
_otp_limiter = login_limiter.__class__()
_reset_limiter = login_limiter.__class__()


def _digest(value: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _send(recipient: str, subject: str, body: str) -> None:
    try:
        send_email(recipient=recipient, subject=subject, body=body)
    except EmailDeliveryError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    users, audit = UserRepository(db), AuditService(db)
    email = users.normalize_email(payload.email)
    key = f"{email}|{request_ip(request)}"

    if login_limiter.is_locked(key):
        audit.log("auth.login_locked", user_email=email, request=request)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много неудачных попыток. Попробуйте позже."
        )

    user = users.get_by_email(email)
    # verify_password вызывается и для несуществующего пользователя, чтобы время ответа не выдавало, есть ли такой email
    password_ok = verify_password(
        payload.password, user.hashed_password if user else "scrypt$16384$8$1$AAAAAAAAAAAAAAAAAAAAAA==$AAAA"
    )
    if user is None or not user.is_active or not password_ok:
        login_limiter.register_failure(key)
        audit.log("auth.login_failed", user_email=email, request=request)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _BAD_CREDENTIALS)
    if not user.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Подтвердите email по ссылке из письма")

    login_limiter.reset(key)
    if settings.two_factor_enabled:
        if not (settings.smtp_host and settings.smtp_from_email):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Для двухфакторной аутентификации настройте SMTP",
            )
        otp_key = f"{email}|{request_ip(request)}"
        if _otp_limiter.is_locked(otp_key):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много кодов. Попробуйте позже.")
        challenge_id, code = secrets.token_urlsafe(32), f"{secrets.randbelow(1_000_000):06d}"
        user.two_factor_challenge_hash = _digest(challenge_id)
        user.two_factor_code_hash = _digest(code)
        user.two_factor_expires_at = utcnow() + timedelta(minutes=10)
        user.two_factor_attempts = 0
        users.save(user)
        _otp_limiter.register_failure(otp_key)
        _send(user.email, "Код входа AqylMed", f"Код подтверждения: {code}\nСрок действия — 10 минут.")
        audit.log("auth.login_2fa_sent", user=user, request=request)
        return TokenResponse(requires_2fa=True, challenge_id=challenge_id, user=UserOut.model_validate(user))
    users.touch_login(user)
    audit.log("auth.login", user=user, request=request)
    return TokenResponse(access_token=create_access_token(user.id, user.role, user.hashed_password), user=UserOut.model_validate(user))


@router.post("/verify-login", response_model=TokenResponse)
def verify_login_code(
    payload: VerifyLoginCodeRequest, request: Request, db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.two_factor_challenge_hash == _digest(payload.challenge_id)
    ).with_for_update().first()
    verify_key = f"verify:{request_ip(request)}"
    if _otp_limiter.is_locked(verify_key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много попыток. Попробуйте позже.")
    if (
        user is None or not user.is_active or user.two_factor_expires_at is None
        or user.two_factor_expires_at <= utcnow() or user.two_factor_attempts >= 5
        or not hmac.compare_digest(user.two_factor_code_hash or "", _digest(payload.code))
    ):
        if user is not None:
            user.two_factor_attempts += 1
            if user.two_factor_attempts >= 5:
                user.two_factor_challenge_hash = None
                user.two_factor_code_hash = None
                user.two_factor_expires_at = None
            db.commit()
        _otp_limiter.register_failure(verify_key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный или просроченный код подтверждения")
    _otp_limiter.reset(verify_key)
    user.two_factor_challenge_hash = None
    user.two_factor_code_hash = None
    user.two_factor_expires_at = None
    user.two_factor_attempts = 0
    user.last_login_at = utcnow()
    db.commit()
    AuditService(db).log("auth.login", user=user, request=request)
    return TokenResponse(access_token=create_access_token(user.id, user.role, user.hashed_password), user=UserOut.model_validate(user))


@router.post("/password-reset/request")
def request_password_reset(
    payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db),
):
    key = f"{request_ip(request)}|{UserRepository.normalize_email(payload.email)}"
    if _reset_limiter.is_locked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много запросов. Попробуйте позже.")
    _reset_limiter.register_failure(key)
    user = UserRepository(db).get_by_email(payload.email)
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        user.password_reset_hash = _digest(token)
        user.password_reset_expires_at = utcnow() + timedelta(minutes=30)
        UserRepository(db).save(user)
        link = f"{settings.password_reset_url}?token={token}"
        _send(user.email, "Сброс пароля AqylMed", f"Для сброса пароля откройте ссылку (действует 30 минут):\n{link}")
    return {"message": _GENERIC_RESET}


@router.post("/verify-email", status_code=204)
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email_verification_hash == _digest(token)).with_for_update().first()
    if (
        user is None or user.email_verification_expires_at is None
        or user.email_verification_expires_at <= utcnow()
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ссылка недействительна или срок её действия истёк")
    user.email_verified = True
    user.email_verification_hash = None
    user.email_verification_expires_at = None
    db.commit()
    return None


@router.post("/password-reset/confirm", status_code=204)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    problem = validate_password_strength(payload.new_password)
    if problem:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, problem)
    user = db.query(User).filter(User.password_reset_hash == _digest(payload.token)).with_for_update().first()
    if user is None or not user.is_active or user.password_reset_expires_at is None or user.password_reset_expires_at <= utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ссылка недействительна или срок её действия истёк")
    if settings.email_notifications_enabled and not (settings.smtp_host and settings.smtp_from_email):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Для email-уведомлений настройте SMTP")
    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_hash = None
    user.password_reset_expires_at = None
    user.two_factor_challenge_hash = None
    user.two_factor_code_hash = None
    user.two_factor_expires_at = None
    db.commit()
    if settings.email_notifications_enabled:
        try:
            send_email(recipient=user.email, subject="Пароль AqylMed изменён",
                       body="Пароль вашей учётной записи был изменён.")
        except EmailDeliveryError:
            logging.getLogger(__name__).exception("Password notification failed for user_id=%s", user.id)
    return None


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/preferences", response_model=UserOut)
def update_preferences(
    payload: UserPreferencesUpdate, user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.locale = payload.locale
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Текущий пароль указан неверно")
    problem = validate_password_strength(payload.new_password)
    if problem:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, problem)
    if settings.email_notifications_enabled and not (settings.smtp_host and settings.smtp_from_email):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Для email-уведомлений настройте SMTP")
    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_hash = None
    user.password_reset_expires_at = None
    user.two_factor_challenge_hash = None
    user.two_factor_code_hash = None
    user.two_factor_expires_at = None
    UserRepository(db).save(user)
    AuditService(db).log("auth.password_changed", user=user, request=request)
    if settings.email_notifications_enabled:
        try:
            send_email(recipient=user.email, subject="Пароль AqylMed изменён",
                       body="Пароль вашей учётной записи был изменён.")
        except EmailDeliveryError:
            logging.getLogger(__name__).exception("Password notification failed for user_id=%s", user.id)
