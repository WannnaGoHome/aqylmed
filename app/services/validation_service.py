"""Автоматическая проверка черновика: каждое число с единицей измерения (доза, температура,
давление, пульс, проценты) должно встречаться в диалоге. Это не заменяет врача, а подсвечивает
места, где ИИ мог «выдумать» значение (риск «Ошибки в числах и дозировках» из техотчёта)."""
import re
from decimal import Decimal, InvalidOperation

from app.schemas.consultation_ai_output import ConsultationAIOutput

_NUM = r"\d+(?:[.,]\d+)?"
_UNIT = (
    r"(?:мг|мкг|mg|mcg|г|гр|мл|ml|ме|ед)(?![\w])"
    r"|(?:грамм|таблет|табл|капсул|капл|единиц|градус)\w*"
    r"|%|°|мм\s*рт|уд(?![\w])"
)
_VALUE_RE = re.compile(rf"(?P<num>{_NUM})\s*(?P<unit>{_UNIT})", re.IGNORECASE)
_ANY_NUM_RE = re.compile(_NUM)
# «38 и 5», «38 точка 5», «38 запятая 5» — так числа часто диктуют
_SPOKEN_DECIMAL_RE = re.compile(r"(\d+)\s+(?:и|точка|запятая)\s+(\d)(?!\d)", re.IGNORECASE)

_UNITS_W = {
    "ноль": 0, "один": 1, "одна": 1, "одну": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5,
    "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11,
    "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16,
    "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
}
_TENS_W = {
    "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
    "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
}
_HUNDREDS_W = {
    "сто": 100, "двести": 200, "триста": 300, "четыреста": 400, "пятьсот": 500,
    "шестьсот": 600, "семьсот": 700, "восемьсот": 800, "девятьсот": 900,
}
_ALL_W = {**_UNITS_W, **_TENS_W, **_HUNDREDS_W}

_SECTION_LABELS = {
    "complaints": "Жалобы", "anamnesis": "Анамнез", "symptoms_duration": "Симптомы и сроки",
    "examination": "Осмотр", "diagnosis": "Диагноз", "treatment_plan": "План лечения",
    "recommendations": "Рекомендации", "memo": "Памятка пациенту",
}


def canonical(number: str) -> str | None:
    try:
        value = Decimal(number.replace(",", ".")).normalize()
    except InvalidOperation:
        return None
    return format(value, "f")


def _spoken_numbers(text: str) -> set[str]:
    """Числа, названные словами: «пятьсот», «тридцать восемь», «двести пятьдесят»."""
    found: set[str] = set()
    run: list[int] = []

    def flush():
        if run:
            found.add(str(sum(run)))
            for part in run:
                found.add(str(part))
            run.clear()

    for word in re.findall(r"[а-яё]+", text.lower()):
        if word in _ALL_W:
            run.append(_ALL_W[word])
        else:
            flush()
    flush()
    return found


def source_numbers(source: str) -> set[str]:
    numbers = {c for m in _ANY_NUM_RE.findall(source) if (c := canonical(m))}
    for whole, frac in _SPOKEN_DECIMAL_RE.findall(source):
        if c := canonical(f"{whole}.{frac}"):
            numbers.add(c)
    return numbers | _spoken_numbers(source)


def find_ungrounded_values(source: str, sections: dict[str, str]) -> list[str]:
    grounded = source_numbers(source)
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()
    for key, text in sections.items():
        for match in _VALUE_RE.finditer(text or ""):
            number, unit = match.group("num"), match.group("unit").strip()
            canon = canonical(number)
            if canon is None or canon in grounded or (canon, unit.lower()) in seen:
                continue
            seen.add((canon, unit.lower()))
            warnings.append(
                f"«{number} {unit}» ({_SECTION_LABELS.get(key, key)}) не найдено в диалоге — проверьте по записи."
            )
    return warnings


def validate_generated_output(dialogue_text: str, output: ConsultationAIOutput) -> list[str]:
    doc = output.medical_document
    sections = {
        "complaints": doc.complaints, "anamnesis": doc.anamnesis,
        "symptoms_duration": doc.symptoms_duration, "examination": doc.examination,
        "diagnosis": doc.diagnosis, "treatment_plan": doc.treatment_plan,
        "recommendations": doc.recommendations, "memo": output.patient_memo.memo_text,
    }
    return find_ungrounded_values(dialogue_text, sections)
