import getpass
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.core.database import SessionLocal

app = typer.Typer(help="AqylMed AI: консольные команды")
console = Console()


def _print_document(document, memo) -> None:
    console.print("\n[bold]Медицинское заключение[/bold]\n")
    for title, value in (
        ("Жалобы", document.complaints),
        ("Анамнез", document.anamnesis),
        ("Симптомы и сроки", document.symptoms_duration),
        ("Осмотр", document.examination),
        ("Диагноз", document.diagnosis),
        ("План лечения", document.treatment_plan),
        ("Рекомендации", document.recommendations),
        ("Неуточнённые данные", document.missing_information),
    ):
        console.print(f"[bold]{title}:[/bold]\n{value or '—'}\n", markup=True, highlight=False)
    console.print("[bold]Памятка пациенту[/bold]\n")
    console.print(memo.memo_text, markup=False)


@app.command()
def generate(
    file_path: str = typer.Option(..., "--file", "-f"),
    patient_name: str = typer.Option(..., "--patient"),
    doctor_name: str = typer.Option(..., "--doctor"),
    consultation_date: str = typer.Option(..., "--date"),
):
    """Текст диалога из файла -> заключение и памятка."""
    from app.services.consultation_service import ConsultationService

    dialogue_text = Path(file_path).read_text(encoding="utf-8")
    with SessionLocal() as db:
        consultation, document, memo = ConsultationService(db).process_text_consultation(
            patient_name=patient_name, doctor_name=doctor_name,
            consultation_date=consultation_date, dialogue_text=dialogue_text,
        )
        console.print(Panel.fit(f"Consultation ID: {consultation.id}", title="AqylMed AI"))
        _print_document(document, memo)


@app.command("from-audio")
def from_audio(
    audio_path: str = typer.Option(..., "--audio", "-a"),
    patient_name: str = typer.Option(..., "--patient"),
    doctor_name: str = typer.Option(..., "--doctor"),
    consultation_date: str = typer.Option(..., "--date"),
):
    """Аудио -> расшифровка -> роли -> заключение и памятка."""
    from app.services.consultation_service import ConsultationService

    with SessionLocal() as db:
        consultation, audio_file, transcript, document, memo = ConsultationService(
            db
        ).process_audio_consultation(
            patient_name=patient_name, doctor_name=doctor_name,
            consultation_date=consultation_date, audio_path=audio_path,
        )
        console.print(Panel.fit(f"Consultation ID: {consultation.id}", title="AqylMed AI"))
        console.print("\n[bold]Расшифровка[/bold]\n")
        console.print(transcript.full_text, markup=False)
        console.print("\n[bold]Диалог с ролями[/bold]\n")
        console.print(transcript.role_separated_text, markup=False)
        console.print("\n[bold]Заметки по очистке[/bold]\n")
        console.print(transcript.cleanup_notes or "Нет заметок", markup=False)
        _print_document(document, memo)


@app.command("from-text")
def from_text(audio_path: str = typer.Option(..., "--audio", "-a")):
    """Только распознавание речи (без заключения): быстро проверить качество STT."""
    from app.services.audio_transcription_service import AudioTranscriptionService

    result = AudioTranscriptionService().transcribe_audio(audio_path)
    console.print("\n[bold]Расшифровка аудио[/bold]\n")
    console.print(result.text, markup=False)


@app.command("benchmark-stt")
def benchmark_stt(
    audio_path: str = typer.Option(..., "--audio", "-a"),
    model: list[str] = typer.Option(
        ..., "--model", "-m",
        help="provider:model, можно несколько. Напр. groq:whisper-large-v3 openai:gpt-4o-transcribe",
    ),
    reference: Path | None = typer.Option(None, "--reference", "-r", help="Эталонная расшифровка (txt) для WER"),
    terms: Path | None = typer.Option(None, "--terms", "-t", help="Файл: по одному мед. термину/числу в строке"),
):
    """Сравнить модели распознавания речи на одной записи: время, цена, WER, медицинские термины."""
    from app.services.benchmark_service import run_benchmark

    ref_text = reference.read_text(encoding="utf-8") if reference else None
    term_list = [t.strip() for t in terms.read_text(encoding="utf-8").splitlines() if t.strip()] if terms else None
    rows = run_benchmark(audio_path, model, ref_text, term_list)

    table = Table(title="Сравнение моделей распознавания речи")
    for column in ("Модель", "Время, с", "Аудио, с", "Цена, $", "WER", "Термины", "Ошибка"):
        table.add_column(column)
    for r in rows:
        table.add_row(
            r.spec, f"{r.seconds:.1f}", f"{r.audio_seconds:.0f}", f"{r.cost_usd:.4f}",
            f"{r.wer:.1%}" if r.wer is not None else "—",
            f"{r.terms_found}/{r.terms_total}" if r.terms_total else "—",
            r.error or "",
        )
    console.print(table)
    for r in rows:
        if r.text:
            console.print(Panel(r.text, title=r.spec), markup=False)


@app.command()
def show(consultation_id: int):
    """Показать сохранённый приём."""
    from app.repositories.consultation_repository import ConsultationRepository

    with SessionLocal() as db:
        c = ConsultationRepository(db).get_by_id(consultation_id)
        if c is None:
            console.print("[red]Приём не найден[/red]")
            raise typer.Exit(1)
        console.print(Panel.fit(f"#{c.id}  {c.patient_name}  статус: {c.status}", title="AqylMed AI"))
        if c.medical_document and c.patient_memo:
            _print_document(c.medical_document, c.patient_memo)


@app.command("create-user")
def create_user(
    email: str = typer.Option(..., "--email"),
    full_name: str = typer.Option(..., "--name"),
    role: str = typer.Option("doctor", "--role", help="doctor | admin"),
    password: str | None = typer.Option(None, "--password", help="Если не указан — спросим безопасно"),
):
    """Создать пользователя (первого администратора удобно создать здесь)."""
    from app.core.security import hash_password, validate_password_strength
    from app.models.user import UserRole
    from app.repositories.user_repository import UserRepository

    if role not in UserRole.ALL:
        console.print("[red]Роль должна быть doctor или admin[/red]")
        raise typer.Exit(1)
    password = password or getpass.getpass("Пароль: ")
    problem = validate_password_strength(password)
    if problem:
        console.print(f"[red]{problem}[/red]")
        raise typer.Exit(1)
    with SessionLocal() as db:
        repo = UserRepository(db)
        if repo.get_by_email(email):
            console.print("[red]Пользователь с таким email уже существует[/red]")
            raise typer.Exit(1)
        user = repo.create(email=email, full_name=full_name, hashed_password=hash_password(password), role=role)
        console.print(f"[green]Создан пользователь #{user.id} ({user.role})[/green]")


@app.command("list-users")
def list_users():
    from app.repositories.user_repository import UserRepository

    table = Table("ID", "Email", "Имя", "Роль", "Активен")
    with SessionLocal() as db:
        for u in UserRepository(db).list():
            table.add_row(str(u.id), u.email, u.full_name, u.role, "да" if u.is_active else "нет")
    console.print(table)


@app.command("purge-audio")
def purge_audio():
    """Удалить аудио старше AUDIO_RETENTION_DAYS (можно запускать из cron)."""
    from app.services.retention_service import AudioRetentionService

    with SessionLocal() as db:
        console.print(f"Удалено аудиозаписей: {AudioRetentionService(db).purge_expired()}")


@app.command()
def usage(month: str | None = typer.Option(None, "--month", help="YYYY-MM")):
    """Расходы на внешние API за месяц."""
    from app.services.usage_service import UsageService

    with SessionLocal() as db:
        s = UsageService(db).summary(month)
    console.print(Panel.fit(
        f"Месяц: {s.month}\nИтого: ${s.total_cost_usd:.4f}\n"
        f"Обработано приёмов: {s.consultations_processed}\n"
        f"Средняя стоимость приёма: "
        f"{'$%.4f' % s.avg_cost_per_consultation_usd if s.avg_cost_per_consultation_usd is not None else '—'}\n"
        f"Бюджет: {'$%.2f (%.1f%%)' % (s.budget_usd, s.budget_used_percent) if s.budget_usd else 'без лимита'}",
        title="Расходы на ИИ"))
    table = Table("Тип", "Провайдер", "Модель", "$", "Мин. аудио", "Токены in/out")
    for m in s.by_model:
        table.add_row(m.kind, m.provider, m.model, f"{m.cost_usd:.4f}", f"{m.audio_minutes:.1f}",
                      f"{m.input_tokens}/{m.output_tokens}")
    console.print(table)


@app.command("check-config")
def check_config():
    """Проверить окружение: БД, ffmpeg, ключи и доступность моделей."""
    from sqlalchemy import text

    from app.core.config import settings
    from app.services.audio_utils import ffmpeg_available

    def line(ok: bool, message: str):
        console.print(f"{'[green]OK[/green]' if ok else '[red]!![/red]'}  {message}")

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        line(True, "база данных доступна")
    except Exception as exc:
        line(False, f"база данных недоступна: {type(exc).__name__}")
    line(ffmpeg_available(), "ffmpeg (нужен для mp3/m4a/webm и сжатия записей)")
    if settings.secret_key:
        line(True, "SECRET_KEY задан")
    else:
        line(not settings.is_production, "SECRET_KEY не задан" + (
            "" if not settings.is_production else " (в production обязателен)"))

    if settings.gemini_api_key:
        try:
            from google import genai

            with genai.Client(api_key=settings.gemini_api_key) as client:
                client.models.get(model=settings.gemini_model)
            line(True, f"модель Gemini доступна: {settings.gemini_model}")
        except Exception as exc:
            line(False, f"модель Gemini «{settings.gemini_model}» недоступна ({type(exc).__name__}). "
                        "Проверьте ai.google.dev/gemini-api/docs/deprecations и GEMINI_MODEL")
    else:
        line(False, "GEMINI_API_KEY НЕ задан")

    key = settings.groq_api_key if settings.stt_provider == "groq" else settings.openai_api_key
    line(bool(key), f"ключ распознавания речи ({settings.stt_provider}) " + ("задан" if key else "НЕ задан"))
    if settings.diarization_enabled:
        line(bool(settings.hf_token), "HF_TOKEN для pyannote " + ("задан" if settings.hf_token else "НЕ задан"))
        try:
            import pyannote.audio  # noqa: F401
            import torch  # noqa: F401
            line(True, "torch и pyannote.audio установлены")
        except ImportError:
            line(False, "torch/pyannote не установлены (pip install -r requirements-audio.txt)")
    else:
        console.print("--  диаризация выключена: роли определяет языковая модель")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """Запустить веб-приложение."""
    import uvicorn

    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
