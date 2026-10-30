from ai_service import AIServiceError

# The ten test records from the assignment, entered exactly as given
TASK_RECORDS = [
    ("Robyn Pears", "28.01.1960", "robyn@gmail.com", "232", "13.5", "180"),
    ("John Hunter", "10.12.1990", "hunter@gmail", "94", "15", "200"),
    ("Darryl Tim", "12.11.1993", "timd@smh.com.au", "240", "18.6", "326"),
    ("Peter Larry", "31.11.2001", "Larry@hotmail.com", "88", "11.5", "165"),
    ("Sam Kerr", "09.12.2006", "sam@news.com.au", "198", "8.9", "192"),
    ("Robyn Pears", "28.01.1960", "robyn@gmail.com", "232", "13.5", "180"),
    ("Madison XI", "12.09.1998", "madison@hotmail.com", "85", "7.6", "163"),
    ("Kris Wu", "19.10.2030", "Kris.wu.gmail.com", "79", "16.5", "197"),
    ("Tenille Singh", "30.11.1991", "Tenille@yahoo.com", "101", "15", "310"),
    ("Prem Kumar", "28.04.1990", "prem@telstra.com", "155", "12.5", "265"),
]

FIELDS = ("full_name", "date_of_birth", "email", "glucose", "haemoglobin", "cholesterol")


def as_payload(record):
    return dict(zip(FIELDS, record))


def create(client, record):
    return client.post("/api/patients", json=as_payload(record))


def test_task_records_are_saved_or_rejected_correctly(client):
    responses = [create(client, record) for record in TASK_RECORDS]

    assert [r.status_code for r in responses] == [201, 400, 201, 400, 201, 409, 201, 400, 201, 201]
    assert set(responses[1].json["errors"]) == {"email"}
    assert set(responses[3].json["errors"]) == {"date_of_birth"}
    assert "already exists" in responses[5].json["errors"]["record"]
    assert set(responses[7].json["errors"]) == {"date_of_birth", "email"}

    patients = client.get("/api/patients").json["patients"]
    assert len(patients) == 6
    assert all(p["risk_level"] and p["remarks"] for p in patients)
    assert patients[0]["date_of_birth"] == "28/01/1960"


def test_update_email_keeps_existing_prediction(client, monkeypatch):
    patient = create(client, TASK_RECORDS[0]).json["patient"]

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("AI should not be called when only the email changes")

    monkeypatch.setattr("routes.predict_health_risk", fail_if_called)
    payload = {**as_payload(TASK_RECORDS[0]), "email": "gokul@infocare.com"}
    response = client.put(f"/api/patients/{patient['id']}", json=payload)

    assert response.status_code == 200
    assert response.json["patient"]["email"] == "gokul@infocare.com"
    assert response.json["patient"]["remarks"] == patient["remarks"]


def test_update_blood_values_refreshes_prediction(client):
    patient = create(client, TASK_RECORDS[6]).json["patient"]
    assert patient["risk_level"] == "Low"

    payload = {**as_payload(TASK_RECORDS[6]), "glucose": "250"}
    response = client.put(f"/api/patients/{patient['id']}", json=payload)

    assert response.json["patient"]["risk_level"] == "High"


def test_update_rejects_invalid_data_and_duplicates(client):
    first = create(client, TASK_RECORDS[0]).json["patient"]
    second = create(client, TASK_RECORDS[2]).json["patient"]

    invalid = client.put(f"/api/patients/{second['id']}", json={**as_payload(TASK_RECORDS[2]), "glucose": "abc"})
    duplicate = client.put(f"/api/patients/{second['id']}", json=as_payload(TASK_RECORDS[0]))
    unchanged = client.put(f"/api/patients/{first['id']}", json=as_payload(TASK_RECORDS[0]))

    assert invalid.status_code == 400
    assert duplicate.status_code == 409
    assert unchanged.status_code == 200


def test_delete_removes_record(client):
    patient = create(client, TASK_RECORDS[0]).json["patient"]

    assert client.delete(f"/api/patients/{patient['id']}").status_code == 200
    assert client.get(f"/api/patients/{patient['id']}").status_code == 404
    assert client.get("/api/patients").json["patients"] == []


def test_records_include_abnormal_value_flags(client):
    patient = create(client, TASK_RECORDS[4]).json["patient"]

    assert patient["flags"] == {"glucose": "high", "haemoglobin": "low", "cholesterol": "normal"}


def test_export_csv(client):
    create(client, TASK_RECORDS[0])
    create(client, TASK_RECORDS[2])

    response = client.get("/api/patients/export.csv")
    lines = response.get_data(as_text=True).lstrip("﻿").splitlines()

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    assert lines[0].startswith("ID,Full Name,Date of Birth,Email")
    assert len(lines) == 3
    assert "Robyn Pears,28/01/1960,robyn@gmail.com" in lines[1]


def test_missing_record_returns_404(client):
    assert client.put("/api/patients/999", json=as_payload(TASK_RECORDS[0])).status_code == 404
    assert client.delete("/api/patients/999").status_code == 404


def test_ai_failure_still_saves_record_and_can_be_retried(client, monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise AIServiceError("The AI service did not respond in time.")

    monkeypatch.setattr("routes.predict_health_risk", unavailable)
    response = create(client, TASK_RECORDS[0])

    assert response.status_code == 201
    assert "warning" in response.json
    assert response.json["patient"]["risk_level"] is None
    patient_id = response.json["patient"]["id"]
    assert client.post(f"/api/patients/{patient_id}/remarks").status_code == 502

    monkeypatch.setattr(
        "routes.predict_health_risk",
        lambda *_args, **_kwargs: {"risk_level": "High", "remarks": "Glucose is high."},
    )
    retried = client.post(f"/api/patients/{patient_id}/remarks")

    assert retried.status_code == 200
    assert retried.json["patient"]["risk_level"] == "High"
