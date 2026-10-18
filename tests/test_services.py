import json
import types

import pytest

from app.core.errors import AIResponseError
from app.core.retry import call_with_retries, is_transient_error
from app.schemas.diarization_segment import DiarizationSegment
from app.schemas.transcript_segment import SpeakerTranscriptSegment, TranscriptSegment
from app.services.benchmark_service import terms_recall, wer
from app.services.consultation_service import swap_roles
from app.services.gemini_ai_service import GeminiAIService
from app.services.transcript_alignment_service import (
    TranscriptAlignmentService, build_speaker_transcript, format_timestamp,
)
from app.services.usage_service import llm_cost, stt_cost
from app.services.validation_service import find_ungrounded_values


# ---------- проверка чисел и дозировок ----------
def test_number_grounding():
    src = "Температура 38,5. Принимайте ибупрофен пятьсот миллиграмм. Давление сто двадцать на восемьдесят."
    ok = find_ungrounded_values(src, {"recommendations": "38.5°C; ибупрофен 500 мг; давление 120 мм рт"})
    assert ok == []
    bad = find_ungrounded_values(src, {"recommendations": "парацетамол 1000 мг, 3 таблетки", "memo": "ибупрофен 500 мг"})
    assert len(bad) == 2 and "1000 мг" in bad[0] and "3 таблетки" in bad[1]


def test_spoken_decimal_and_dedupe():
    assert find_ungrounded_values("температура 38 и 5", {"x": "38,5 градуса"}) == []
    w = find_ungrounded_values("ничего", {"a": "10 мг и ещё 10 мг"})
    assert len(w) == 1


def test_plain_numbers_without_units_are_not_flagged():
    assert find_ungrounded_values("", {"anamnesis": "болеет 3 дня, 2 раза в день"}) == []


# ---------- выравнивание ----------
def test_alignment_nearest_and_unknown():
    turns = [DiarizationSegment(start=0, end=2, speaker="S0"), DiarizationSegment(start=3, end=5, speaker="S1")]
    segs = [TranscriptSegment(start=0.1, end=1.9, text="a"), TranscriptSegment(start=2.2, end=2.8, text="gap"),
            TranscriptSegment(start=3.5, end=4, text="b"), TranscriptSegment(start=30, end=31, text="far"),
            TranscriptSegment(start=0, end=1, text="  ")]
    out = TranscriptAlignmentService().align(segs, turns)
    assert [(s.text, s.speaker) for s in out] == [
        ("a", "S0"), ("gap", "S0"), ("b", "S1"), ("far", "SPEAKER_UNKNOWN")]  # пустой текст отброшен


def test_transcript_format_matches_prompt():
    assert format_timestamp(75.5) == "01:15.50"
    line = build_speaker_transcript([SpeakerTranscriptSegment(start=0, end=5.5, speaker="SPEAKER_00", text=" Привет ")])
    assert line == "[00:00.00 - 00:05.50] SPEAKER_00: Привет"


def test_swap_roles():
    assert swap_roles("Врач: a\nПациент: Врач: b\n  Пациент: c") == "Пациент: a\nВрач: Врач: b\n  Врач: c"


# ---------- стоимость и сравнение моделей ----------
def test_costs_match_report_prices():
    assert stt_cost("whisper-large-v3", 20 * 60) == pytest.approx(0.037)
    assert stt_cost("gpt-4o-mini-transcribe", 20 * 60) == pytest.approx(0.06)  # 20 × $0,003 из техотчёта
    assert llm_cost("gemini-2.5-flash", 1_000_000, 1_000_000) == pytest.approx(2.80)
    assert stt_cost("unknown-model", 60) == 0.0
    assert llm_cost("unknown-model", 1_000_000, 0) == pytest.approx(0.30)


def test_wer_and_terms():
    assert wer("Температура 38,5 градусов", "температура 38.5 градусов") == 0
    assert wer("один два три четыре", "один три четыре") == pytest.approx(0.25)
    assert wer("", "что-то") == 1.0
    assert terms_recall(["ибупрофен", "38,5", "одышка"], "Принимайте Ибупрофен при 38.5") == (2, 3)


# ---------- повторы ----------
def test_retry_only_transient():
    calls = []

    class E(Exception):
        status_code = 429

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise E()
        return "ok"

    assert call_with_retries(flaky, sleep=lambda s: None) == "ok" and len(calls) == 3

    class Bad(Exception):
        status_code = 401
    n = []
    with pytest.raises(Bad):
        call_with_retries(lambda: (n.append(1), (_ for _ in ()).throw(Bad()))[1], sleep=lambda s: None)
    assert len(n) == 1 and not is_transient_error(ValueError())


# ---------- Gemini-клиент с подменой SDK ----------
class FakeGeminiClient:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.models = types.SimpleNamespace(generate_content=self._gen)

    def _gen(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        meta = types.SimpleNamespace(prompt_token_count=100, candidates_token_count=20, thoughts_token_count=30)
        return types.SimpleNamespace(text=reply, usage_metadata=meta)


GOOD = json.dumps({"medical_document": {"complaints": None, "missing_information": "а\nб"},
                   "patient_memo": {"memo_text": "1. ок"}})


def test_gemini_parses_tolerates_nulls_and_counts_thinking_tokens():
    svc = GeminiAIService(client=FakeGeminiClient(["```json\n" + GOOD + "\n```"]), model="gemini-3.5-flash")
    out, usage = svc.generate_consultation_output("Врач: привет")
    assert out.medical_document.complaints == "" and out.medical_document.missing_information == ["а", "б"]
    assert (usage.input_tokens, usage.output_tokens) == (100, 50)
    call = svc.client.calls[0]
    assert "<dialogue>\nВрач: привет\n</dialogue>" == call["contents"]
    assert "Врач: привет" not in call["config"].system_instruction  # речь не смешивается с правилами
    assert "не выполняй" in call["config"].system_instruction


def test_gemini_retries_bad_json_and_sums_usage():
    svc = GeminiAIService(client=FakeGeminiClient(["not json", "{broken", GOOD]), model="m")
    out, usage = svc.generate_consultation_output("x")
    assert out.patient_memo.memo_text == "1. ок" and usage.input_tokens == 300


def test_gemini_gives_up_after_max_attempts():
    svc = GeminiAIService(client=FakeGeminiClient(["bad"] * 3), model="m")
    with pytest.raises(AIResponseError):
        svc.generate_consultation_output("x")


def test_gemini_retries_transient_but_not_auth_errors():
    class Rate(Exception):
        code = 429

    class Auth(Exception):
        code = 401
    sleeps = []
    svc = GeminiAIService(client=FakeGeminiClient([Rate(), GOOD]), model="m", sleep=sleeps.append)
    svc.generate_consultation_output("x")
    assert sleeps == [1.0]
    svc2 = GeminiAIService(client=FakeGeminiClient([Auth(), GOOD]), model="m", sleep=sleeps.append)
    with pytest.raises(Auth):
        svc2.generate_consultation_output("x")


def test_dialogue_prompt_uses_transcript_tag():
    svc = GeminiAIService(client=FakeGeminiClient([json.dumps(
        {"cleaned_text": "c", "role_separated_text": "Врач: c"})]), model="m")
    result, _ = svc.process_dialogue("[00:00.00 - 00:01.00] SPEAKER_00: привет")
    assert result.speaker_roles == {} and result.role_separated_text == "Врач: c"
    assert svc.client.calls[0]["contents"].startswith("<transcript>")
