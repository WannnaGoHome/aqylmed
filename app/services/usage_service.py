import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import FALLBACK_LLM_PRICE, settings
from app.core.errors import BudgetExceededError
from app.core.timeutils import utcnow
from app.models.usage_record import UsageKind
from app.repositories.usage_repository import UsageRepository
from app.schemas.api import UsageByDay, UsageByModel, UsageSummary
from app.services.gemini_ai_service import LLMUsage

logger = logging.getLogger(__name__)


def stt_cost(model: str, seconds: float) -> float:
    price = settings.stt_prices_per_minute.get(model)
    if price is None:
        logger.warning("Нет тарифа STT для модели %s — стоимость учтена как 0", model)
        return 0.0
    return seconds / 60.0 * price


def llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_price, out_price = settings.llm_prices_per_million.get(model, FALLBACK_LLM_PRICE)
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000


def month_bounds(month: str | None = None) -> tuple[datetime, datetime]:
    """month = 'YYYY-MM'; по умолчанию текущий (UTC)."""
    now = utcnow()
    year, mon = (now.year, now.month) if not month else (int(month[:4]), int(month[5:7]))
    start = datetime(year, mon, 1)
    end = datetime(year + (mon == 12), 1 if mon == 12 else mon + 1, 1)
    return start, end


class UsageService:
    def __init__(self, db: Session):
        self.repo = UsageRepository(db)

    def record_stt(self, consultation_id: int | None, provider: str, model: str, seconds: float) -> float:
        cost = stt_cost(model, seconds)
        self.repo.add(
            consultation_id=consultation_id, kind=UsageKind.STT, provider=provider,
            model=model, audio_seconds=seconds, cost_usd=cost,
        )
        return cost

    def record_llm(self, consultation_id: int | None, provider: str, usage: LLMUsage) -> float:
        cost = llm_cost(usage.model, usage.input_tokens, usage.output_tokens)
        self.repo.add(
            consultation_id=consultation_id, kind=UsageKind.LLM, provider=provider, model=usage.model,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, cost_usd=cost,
        )
        return cost

    def check_budget(self) -> None:
        limit = settings.monthly_api_budget_usd
        if limit <= 0:
            return
        start, end = month_bounds()
        if self.repo.total_cost(start, end) >= limit:
            raise BudgetExceededError(
                f"Месячный лимит расходов на ИИ (${limit:.2f}) исчерпан. Обратитесь к администратору."
            )

    def summary(self, month: str | None = None) -> UsageSummary:
        start, end = month_bounds(month)
        total = self.repo.total_cost(start, end)
        count = self.repo.consultations_count(start, end)
        budget = settings.monthly_api_budget_usd
        return UsageSummary(
            month=f"{start.year:04d}-{start.month:02d}",
            total_cost_usd=round(total, 6),
            budget_usd=budget,
            budget_used_percent=round(total / budget * 100, 1) if budget > 0 else None,
            consultations_processed=count,
            avg_cost_per_consultation_usd=round(total / count, 6) if count else None,
            by_model=[
                UsageByModel(
                    kind=k, provider=p, model=m, cost_usd=round(c or 0, 6),
                    audio_minutes=round((s or 0) / 60, 2), input_tokens=int(i or 0), output_tokens=int(o or 0),
                )
                for k, p, m, c, s, i, o in self.repo.by_model(start, end)
            ],
            by_day=[UsageByDay(day=str(d), cost_usd=round(c or 0, 6)) for d, c in self.repo.by_day(start, end)],
        )
