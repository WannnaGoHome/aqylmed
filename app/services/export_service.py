import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from app.models.consultation import Consultation, ConsultationStatus

SECTIONS = [
    ("complaints", "Жалобы"),
    ("anamnesis", "Анамнез"),
    ("symptoms_duration", "Симптомы и их продолжительность"),
    ("examination", "Объективные данные"),
    ("diagnosis", "Заключение (диагноз)"),
    ("treatment_plan", "План лечения"),
    ("recommendations", "Рекомендации"),
]


def _status_line(c: Consultation) -> str:
    if c.status == ConsultationStatus.CONFIRMED and c.confirmed_at:
        who = c.confirmed_by.full_name if c.confirmed_by else c.doctor_name
        return f"Подтверждено врачом: {who}, {c.confirmed_at:%d.%m.%Y %H:%M}"
    return "ЧЕРНОВИК: не подтверждён врачом"


def _missing(doc) -> list[str]:
    return [line for line in (doc.missing_information or "").splitlines() if line.strip()]


def export_txt(c: Consultation) -> str:
    doc, memo = c.medical_document, c.patient_memo
    lines = [
        "МЕДИЦИНСКОЕ ЗАКЛЮЧЕНИЕ",
        f"Пациент: {c.patient_name}",
        f"Врач: {c.doctor_name}",
        f"Дата приёма: {c.consultation_date}",
        _status_line(c),
        "",
    ]
    if doc:
        for key, title in SECTIONS:
            lines += [f"{title}:", getattr(doc, key) or "не указано", ""]
        if _missing(doc):
            lines += ["Требует уточнения:"] + [f"- {m}" for m in _missing(doc)] + [""]
    if memo:
        lines += ["ПАМЯТКА ПАЦИЕНТУ", memo.memo_text, ""]
    lines.append("Документ подготовлен с помощью AqylMed AI и должен быть проверен врачом.")
    return "\n".join(lines)


def export_docx(c: Consultation) -> bytes:
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    title = document.add_heading("Медицинское заключение", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for label, value in (("Пациент", c.patient_name), ("Врач", c.doctor_name),
                         ("Дата приёма", c.consultation_date)):
        p = document.add_paragraph()
        p.add_run(f"{label}: ").bold = True
        p.add_run(value)
    status = document.add_paragraph()
    run = status.add_run(_status_line(c))
    run.bold = True
    run.italic = c.status != ConsultationStatus.CONFIRMED

    doc, memo = c.medical_document, c.patient_memo
    if doc:
        for key, title_text in SECTIONS:
            document.add_heading(title_text, level=2)
            document.add_paragraph(getattr(doc, key) or "не указано")
        if _missing(doc):
            document.add_heading("Требует уточнения", level=2)
            for item in _missing(doc):
                document.add_paragraph(item, style="List Bullet")
    if memo:
        document.add_page_break()
        document.add_heading("Памятка пациенту", level=1)
        for line in memo.memo_text.splitlines():
            document.add_paragraph(line)

    footer = document.add_paragraph()
    note = footer.add_run("Документ подготовлен с помощью AqylMed AI и должен быть проверен врачом.")
    note.italic = True
    note.font.size = Pt(9)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
