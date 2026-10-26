import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


def send_email(*, recipient: str, subject: str, body: str) -> None:
    if not all((settings.smtp_host, settings.smtp_from_email)):
        raise EmailDeliveryError("Почтовый сервис не настроен: задайте SMTP_HOST и SMTP_FROM_EMAIL")

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.exception("Не удалось отправить письмо получателю %s", recipient)
        raise EmailDeliveryError("Не удалось отправить письмо. Попробуйте позже.") from exc
