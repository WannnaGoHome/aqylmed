from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC now (колонки в БД хранят naive UTC). Замена устаревшему datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
