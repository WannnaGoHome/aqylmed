import logging
import time
from typing import Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

_TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
_TRANSIENT_NAMES = {
    "APIConnectionError", "APITimeoutError", "ServerError",
    "ReadTimeout", "ConnectTimeout", "ConnectError", "RemoteProtocolError",
}


def is_transient_error(exc: BaseException) -> bool:
    """Ошибки, которые имеет смысл повторить: лимиты, 5xx, обрывы сети."""
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = getattr(exc, "code", None)
    if isinstance(status, int) and status in _TRANSIENT_STATUS:
        return True
    if type(exc).__name__ in _TRANSIENT_NAMES:
        return True
    return isinstance(exc, httpx.TransportError)


def call_with_retries(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    sleep: Callable[[float], None] = time.sleep,
    is_transient: Callable[[BaseException], bool] = is_transient_error,
    label: str = "external call",
) -> T:
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt >= attempts or not is_transient(exc):
                raise
            delay = min(max_delay, base_delay * 2 ** (attempt - 1))
            logger.warning(
                "%s failed (%s), retry %d/%d in %.1fs",
                label, type(exc).__name__, attempt, attempts - 1, delay,
            )
            sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover
