import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import admin, auth, consultations
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.consultation_repository import ConsultationRepository
from app.repositories.user_repository import UserRepository
from app.services.retention_service import AudioRetentionService

logger = logging.getLogger("aqylmed")

_PURGE_INTERVAL_SECONDS = 6 * 3600

_CSP = (
    "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
    "style-src 'self'; script-src 'self'; connect-src 'self'; font-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


def bootstrap() -> None:
    """Однократные действия при старте: первый администратор, зависшие задачи."""
    with SessionLocal() as db:
        users = UserRepository(db)
        if users.count() == 0 and settings.bootstrap_admin_email and settings.bootstrap_admin_password:
            users.create(
                email=settings.bootstrap_admin_email, full_name="Администратор",
                hashed_password=hash_password(settings.bootstrap_admin_password), role=UserRole.ADMIN,
            )
            logger.info("Создан первый администратор %s", settings.bootstrap_admin_email)
        stuck = ConsultationRepository(db).fail_all_processing(
            "Обработка прервана перезапуском сервера. Нажмите «Повторить обработку»."
        )
        if stuck:
            logger.warning("Помечено как неудачные зависшие консультации: %d", stuck)


def purge_audio_once() -> None:
    try:
        with SessionLocal() as db:
            AudioRetentionService(db).purge_expired()
    except Exception:
        logger.exception("Ошибка очистки старых аудиозаписей")


async def _purge_loop():
    while True:
        await asyncio.to_thread(purge_audio_once)
        await asyncio.sleep(_PURGE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.jwt_secret  # в production падаем сразу, если SECRET_KEY не задан
    bootstrap()
    task = asyncio.create_task(_purge_loop())
    try:
        yield
    finally:
        task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AqylMed AI",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware, allow_origins=settings.cors_origin_list,
            allow_methods=["*"], allow_headers=["*"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not path.startswith(("/docs", "/openapi.json")):
            response.headers["Content-Security-Policy"] = _CSP
            response.headers["X-Frame-Options"] = "DENY"
        if path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health", tags=["system"])
    def health():
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
        except Exception:
            return {"status": "error", "database": False}
        return {"status": "ok", "database": True}

    app.include_router(auth.router)
    app.include_router(consultations.router)
    app.include_router(admin.router)

    if settings.static_dir.exists():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")
    return app


app = create_app()
