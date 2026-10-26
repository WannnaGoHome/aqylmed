import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.medical_catalog import Icd10Code, MedicalDocumentTemplate, MedicalSpecialty
from app.models.user import User
from app.schemas.api import (
    DocumentType, Icd10EntryInput, MedicalSpecialtyOut, MedicalTemplateInput, MedicalTemplateOut, SpecialtyInput,
)

router = APIRouter(prefix="/api/catalog", tags=["medical catalog"])
_SECTION_KEYS = {
    "complaints", "anamnesis", "symptoms_duration", "examination", "diagnosis",
    "diagnosis_code", "treatment_plan", "recommendations",
}


@router.get("/specialties", response_model=list[MedicalSpecialtyOut])
def list_specialties(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(MedicalSpecialty).filter(MedicalSpecialty.is_active.is_(True)).order_by(
        MedicalSpecialty.name_ru
    ).all()


@router.get("/template", response_model=MedicalTemplateOut)
def get_template(
    locale: str = Query(default="ru", pattern=r"^(ru|kk|en)$"),
    document_type: DocumentType = "initial",
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if user.specialty_id is None:
        return MedicalTemplateOut(specialty_id=0, locale=locale, document_type=document_type, fields={})
    template = db.query(MedicalDocumentTemplate).filter_by(
        specialty_id=user.specialty_id, locale=locale, document_type=document_type
    ).first()
    return MedicalTemplateOut(
        specialty_id=user.specialty_id, locale=locale, document_type=document_type,
        fields=json.loads(template.fields_json) if template else {},
    )


@router.get("/specialties/{specialty_id}/template", response_model=MedicalTemplateOut,
            dependencies=[Depends(require_admin)])
def get_specialty_template(
    specialty_id: int, locale: str = Query(default="ru", pattern=r"^(ru|kk|en)$"),
    document_type: DocumentType = "initial",
    db: Session = Depends(get_db),
):
    if db.get(MedicalSpecialty, specialty_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Специальность не найдена")
    template = db.query(MedicalDocumentTemplate).filter_by(
        specialty_id=specialty_id, locale=locale, document_type=document_type
    ).first()
    return MedicalTemplateOut(
        specialty_id=specialty_id, locale=locale, document_type=document_type,
        fields=json.loads(template.fields_json) if template else {},
    )


@router.get("/icd10")
def search_icd10(
    q: str = Query(min_length=2, max_length=100),
    locale: str = Query(default="ru", pattern=r"^(ru|kk|en)$"),
    limit: int = Query(default=20, ge=1, le=50),
    _user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    name_column = {"ru": Icd10Code.name_ru, "kk": Icd10Code.name_kk, "en": Icd10Code.name_en}[locale]
    matches = db.query(Icd10Code).filter(
        Icd10Code.is_active.is_(True),
        or_(Icd10Code.code.ilike(f"%{q}%"), name_column.ilike(f"%{q}%"),
            Icd10Code.name_ru.ilike(f"%{q}%")),
    ).order_by(Icd10Code.code).limit(limit).all()
    return [{"code": item.code, "name": getattr(item, f"name_{locale}") or item.name_ru} for item in matches]


@router.put("/icd10", status_code=200, dependencies=[Depends(require_admin)])
def import_icd10(
    entries: list[Icd10EntryInput], db: Session = Depends(get_db),
):
    if not entries or len(entries) > 100000:
        raise HTTPException(413, "Загрузите от 1 до 100000 кодов")
    codes = list({entry.code.upper() for entry in entries})
    existing = {}
    for offset in range(0, len(codes), 1000):
        existing.update({item.code: item for item in db.query(Icd10Code).filter(
            Icd10Code.code.in_(codes[offset:offset + 1000])
        ).all()})
    for entry in entries:
        code = entry.code.upper()
        item = existing.get(code)
        if item is None:
            item = Icd10Code(code=code)
            db.add(item)
            existing[code] = item
        item.name_ru, item.name_kk, item.name_en = entry.name_ru, entry.name_kk, entry.name_en
        item.is_active = True
    db.commit()
    return {"upserted": len(entries)}


@router.post("/specialties", response_model=MedicalSpecialtyOut, status_code=201,
             dependencies=[Depends(require_admin)])
def create_specialty(payload: SpecialtyInput, db: Session = Depends(get_db)):
    specialty = MedicalSpecialty(**payload.model_dump())
    db.add(specialty)
    db.commit()
    db.refresh(specialty)
    return specialty


@router.put("/specialties/{specialty_id}/template", response_model=MedicalTemplateOut,
            dependencies=[Depends(require_admin)])
def save_template(
    specialty_id: int, payload: MedicalTemplateInput, db: Session = Depends(get_db),
):
    if set(payload.fields) - _SECTION_KEYS:
        raise HTTPException(422, "Шаблон содержит неизвестные поля")
    if any(not label.strip() or len(label) > 100 for label in payload.fields.values()):
        raise HTTPException(422, "Подписи полей должны содержать 1–100 символов")
    if db.get(MedicalSpecialty, specialty_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Специальность не найдена")
    template = db.query(MedicalDocumentTemplate).filter_by(
        specialty_id=specialty_id, locale=payload.locale, document_type=payload.document_type
    ).first()
    if template is None:
        template = MedicalDocumentTemplate(specialty_id=specialty_id, locale=payload.locale, document_type=payload.document_type)
        db.add(template)
    template.fields_json = json.dumps(payload.fields, ensure_ascii=False)
    db.commit()
    return MedicalTemplateOut(specialty_id=specialty_id, locale=payload.locale, document_type=payload.document_type, fields=payload.fields)


@router.put("/specialties", dependencies=[Depends(require_admin)])
def import_specialties(entries: list[SpecialtyInput], db: Session = Depends(get_db)):
    if not entries or len(entries) > 5000:
        raise HTTPException(422, "Загрузите от 1 до 5000 специальностей")
    for entry in entries:
        name = entry.name_ru.strip()
        if not name:
            raise HTTPException(422, "Название специальности не может быть пустым")
        item = db.query(MedicalSpecialty).filter_by(name_ru=name).first()
        if item is None:
            item = MedicalSpecialty(name_ru=name)
            db.add(item)
        item.name_kk, item.name_en = entry.name_kk.strip(), entry.name_en.strip()
        item.is_active = True
        db.flush()
    db.commit()
    return {"upserted": len(entries)}
