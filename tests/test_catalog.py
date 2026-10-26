from tests.conftest import TEXT_PAYLOAD


def test_admin_can_create_specialty_template_and_import_icd(client, admin, doctor):
    created = client.post("/api/catalog/specialties", headers=admin, json={
        "name_ru": "Терапия", "name_kk": "Терапия", "name_en": "Internal medicine",
    })
    assert created.status_code == 201
    specialty_id = created.json()["id"]
    template = {"locale": "en", "fields": {"diagnosis": "Assessment", "diagnosis_code": "ICD-10 code"}}
    saved = client.put(
        f"/api/catalog/specialties/{specialty_id}/template", headers=admin, json=template
    )
    assert saved.status_code == 200 and saved.json()["fields"] == template["fields"]
    imported = client.put("/api/catalog/icd10", headers=admin, json=[{
        "code": "J06.9", "name_ru": "Острая инфекция верхних дыхательных путей",
        "name_kk": "Жоғарғы тыныс жолдарының жедел инфекциясы", "name_en": "Acute upper respiratory infection",
    }])
    assert imported.status_code == 200 and imported.json()["upserted"] == 1
    result = client.get("/api/catalog/icd10?q=J06&locale=en", headers=doctor)
    assert result.status_code == 200 and result.json() == [
        {"code": "J06.9", "name": "Acute upper respiratory infection"}
    ]


def test_diagnosis_requires_valid_code_once_catalog_loaded(client, admin, doctor):
    client.put("/api/catalog/icd10", headers=admin, json=[{
        "code": "J06.9", "name_ru": "Острая инфекция верхних дыхательных путей",
    }])
    response = client.post("/api/consultations/text", headers=doctor, json=TEXT_PAYLOAD)
    assert response.status_code == 202
    cid = response.json()["id"]
    missing = client.put(
        f"/api/consultations/{cid}/document", headers=doctor, json={"diagnosis": "ОРВИ"}
    )
    assert missing.status_code == 422
    invalid = client.put(
        f"/api/consultations/{cid}/document", headers=doctor,
        json={"diagnosis": "ОРВИ", "diagnosis_code": "Z99.9"},
    )
    assert invalid.status_code == 422
    valid = client.put(
        f"/api/consultations/{cid}/document", headers=doctor,
        json={"diagnosis": "ОРВИ", "diagnosis_code": "J06.9"},
    )
    assert valid.status_code == 200 and valid.json()["document"]["diagnosis_code"] == "J06.9"
