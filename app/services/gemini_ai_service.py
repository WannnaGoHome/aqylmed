import logging
import re
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import AIResponseError, ConfigurationError
from app.core.retry import is_transient_error
from app.schemas.consultation_ai_output import ConsultationAIOutput
from app.schemas.dialogue_processing import DialogueProcessingResult

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMUsage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0  # включая токены «рассуждений», они тарифицируются как output


class GeminiAIService:
    provider_name = "gemini"

    def __init__(self, client=None, model: str | None = None, sleep: Callable[[float], None] = time.sleep):
        if client is None:
            if not settings.gemini_api_key:
                raise ConfigurationError("GEMINI_API_KEY не задан в .env")
            from google import genai

            client = genai.Client(api_key=settings.gemini_api_key)
        self.client = client
        self.model = model or settings.gemini_model
        self._sleep = sleep

    # ---------- промпты ----------
    def _load_prompt(self, prompt_name: str) -> str:
        return (settings.prompts_dir / prompt_name).read_text(encoding="utf-8")

    def _build(self, prompt_name: str, placeholder: str, tag: str, payload: str) -> tuple[str, str]:
        """Инструкции идут в system_instruction, а речь пациента — отдельно, в теги данных.
        Так слова из записи не смешиваются с правилами."""
        template = self._load_prompt(prompt_name).replace("\r\n", "\n")
        instructions = template.split(placeholder)[0].rstrip()
        return instructions, f"<{tag}>\n{payload}\n</{tag}>"

    def _extract_json_object(self, content: str) -> str:
        content = content.strip()

        if content.startswith("```json"):
            content = content.removeprefix("```json").strip()

        if content.startswith("```"):
            content = content.removeprefix("```").strip()

        if content.endswith("```"):
            content = content.removesuffix("```").strip()

        match = re.search(r"\{.*\}", content, re.DOTALL)

        if not match:
            raise ValueError("В ответе модели не найден JSON")

        return match.group(0)

    # ---------- вызов модели ----------
    def _generate_structured(
        self, system_instruction: str, contents: str, schema_model: type[T]
    ) -> tuple[T, LLMUsage]:
        from google.genai import types

        total = LLMUsage(model=self.model)
        attempts = max(1, settings.llm_max_attempts)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )
            except Exception as exc:
                if attempt >= attempts or not is_transient_error(exc):
                    raise
                delay = min(8.0, 2.0 ** (attempt - 1))
                logger.warning("Gemini transient error (%s), retry in %.0fs", type(exc).__name__, delay)
                self._sleep(delay)
                last_error = exc
                continue

            meta = getattr(response, "usage_metadata", None)
            total.input_tokens += getattr(meta, "prompt_token_count", 0) or 0
            total.output_tokens += (getattr(meta, "candidates_token_count", 0) or 0) + (
                getattr(meta, "thoughts_token_count", 0) or 0
            )

            content = response.text
            if not content:
                last_error = AIResponseError("Модель вернула пустой ответ")
                continue
            try:
                try:
                    return schema_model.model_validate_json(content), total
                except ValueError:
                    return schema_model.model_validate_json(self._extract_json_object(content)), total
            except ValueError as exc:  # включает pydantic.ValidationError
                last_error = exc
                logger.warning("Gemini returned invalid JSON (attempt %d/%d)", attempt, attempts)

        raise AIResponseError(
            "Модель не вернула корректный структурированный ответ. Повторите попытку."
        ) from last_error

    # ---------- публичные методы ----------
    def process_dialogue(self, speaker_transcript: str) -> tuple[DialogueProcessingResult, LLMUsage]:
        system, contents = self._build(
            "dialogue_processing_prompt.txt", "{speaker_transcript}", "transcript", speaker_transcript
        )
        return self._generate_structured(system, contents, DialogueProcessingResult)

    def generate_consultation_output(self, dialogue_text: str) -> tuple[ConsultationAIOutput, LLMUsage]:
        system, contents = self._build(
            "consultation_output_prompt.txt", "{dialogue_text}", "dialogue", dialogue_text
        )
        return self._generate_structured(system, contents, ConsultationAIOutput)
