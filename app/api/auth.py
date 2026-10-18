from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, login_limiter, request_ip
from app.core.database import get_db
from app.core.security import (
    create_access_token, hash_password, validate_password_strength, verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.api import ChangePasswordRequest, LoginRequest, TokenResponse, UserOut
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/auth", tags=["auth"])

_BAD_CREDENTIALS = "Неверный email или пароль"


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

    login_limiter.reset(key)
    users.touch_login(user)
    audit.log("auth.login", user=user, request=request)
    return TokenResponse(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
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
    user.hashed_password = hash_password(payload.new_password)
    UserRepository(db).save(user)
    AuditService(db).log("auth.password_changed", user=user, request=request)
