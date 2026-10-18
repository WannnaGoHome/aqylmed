class ConfigurationError(Exception):
    """Не хватает настроек (ключ API, токен и т.п.)."""


class ProcessingError(Exception):
    """Ошибка обработки консультации с понятным для врача текстом."""


class AIResponseError(Exception):
    """Языковая модель вернула неподходящий ответ."""


class BudgetExceededError(Exception):
    """Месячный лимит расходов на внешние API исчерпан."""
