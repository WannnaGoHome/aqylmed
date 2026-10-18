"""Сравнение моделей распознавания речи на одной записи (WER, термины, время, стоимость)."""
import re
import time
from dataclasses import dataclass

from app.services.audio_transcription_service import build_stt_provider
from app.services.usage_service import stt_cost


def normalize_text(text: str) -> list[str]:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"(\d)[,.](\d)", r"\1.\2", text)
    return re.findall(r"[\w.]+", re.sub(r"[^\w\s.]", " ", text))


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize_text(reference), normalize_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref)


def terms_recall(terms: list[str], hypothesis: str) -> tuple[int, int]:
    hyp = " ".join(normalize_text(hypothesis))
    found = sum(1 for t in terms if " ".join(normalize_text(t)) in hyp)
    return found, len(terms)


@dataclass
class BenchmarkRow:
    spec: str
    seconds: float
    audio_seconds: float
    cost_usd: float
    text: str
    wer: float | None = None
    terms_found: int | None = None
    terms_total: int | None = None
    error: str | None = None


def run_benchmark(audio_path: str, specs: list[str], reference: str | None = None,
                  terms: list[str] | None = None) -> list[BenchmarkRow]:
    rows = []
    for spec in specs:
        provider_name, _, model = spec.partition(":")
        try:
            provider = build_stt_provider(provider_name, model or None)
            started = time.perf_counter()
            result = provider.transcribe(audio_path)
            elapsed = time.perf_counter() - started
        except Exception as exc:  # одна упавшая модель не должна ломать сравнение остальных
            rows.append(BenchmarkRow(spec, 0, 0, 0, "", error=f"{type(exc).__name__}: {exc}"))
            continue
        row = BenchmarkRow(spec, elapsed, result.duration_seconds,
                           stt_cost(result.model, result.duration_seconds), result.text)
        if reference:
            row.wer = wer(reference, result.text)
        if terms:
            row.terms_found, row.terms_total = terms_recall(terms, result.text)
        rows.append(row)
    return rows
