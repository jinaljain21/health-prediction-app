"""REST API for patient records: /api/patients"""
import csv
import io
from datetime import date

from flask import Blueprint, Response, current_app, jsonify, request
from sqlalchemy import func

from ai_service import AIServiceError, calculate_age, predict_health_risk
from models import Patient, PredictionCache, db
from validators import validate_patient

api = Blueprint("api", __name__, url_prefix="/api")

# A new AI prediction is only needed when one of these values changes
AI_INPUT_FIELDS = ("date_of_birth", "glucose", "haemoglobin", "cholesterol")

CSV_COLUMNS = [
    ("ID", "id"),
    ("Full Name", "full_name"),
    ("Date of Birth", "date_of_birth"),
    ("Email", "email"),
    ("Glucose (mg/dL)", "glucose"),
    ("Haemoglobin (g/dL)", "haemoglobin"),
    ("Cholesterol (mg/dL)", "cholesterol"),
    ("Risk Level", "risk_level"),
    ("Remarks", "remarks"),
]


def find_duplicate(cleaned, exclude_id=None):
    """Same name, date of birth and email (case-insensitive) counts as the same patient."""
    query = Patient.query.filter(
        func.lower(Patient.full_name) == cleaned["full_name"].lower(),
        Patient.date_of_birth == cleaned["date_of_birth"],
        func.lower(Patient.email) == cleaned["email"].lower(),
    )
    if exclude_id is not None:
        query = query.filter(Patient.id != exclude_id)
    return query.first()


def get_prediction(patient):
    """Return (prediction, from_cache). Uses a saved answer when the same inputs were seen before."""
    inputs = {
        "model": current_app.config["GEMINI_MODEL"],
        "age": calculate_age(patient.date_of_birth),
        "glucose": patient.glucose,
        "haemoglobin": patient.haemoglobin,
        "cholesterol": patient.cholesterol,
    }
    cached = PredictionCache.query.filter_by(**inputs).first()
    if cached:
        return {"risk_level": cached.risk_level, "remarks": cached.remarks}, True

    if not current_app.extensions["ai_rate_limiter"].allow():
        raise AIServiceError("AI request limit reached. Please retry in a minute.")

    prediction = predict_health_risk(
        inputs["age"],
        patient.glucose,
        patient.haemoglobin,
        patient.cholesterol,
        api_key=current_app.config["GEMINI_API_KEY"],
        model=inputs["model"],
        timeout=current_app.config["AI_TIMEOUT_SECONDS"],
    )
    db.session.add(PredictionCache(**inputs, **prediction))
    return prediction, False


def apply_ai_prediction(patient):
    """Fill risk_level and remarks. Returns (error message or None, whether the cache was used)."""
    try:
        prediction, from_cache = get_prediction(patient)
    except AIServiceError as exc:
        current_app.logger.warning("AI prediction failed: %s", exc)
        patient.risk_level = None
        patient.remarks = f"AI prediction unavailable: {exc}"
        return str(exc), False

    patient.risk_level = prediction["risk_level"]
    patient.remarks = prediction["remarks"]
    return None, from_cache


def saved_response(patient, ai_error, from_cache, status):
    body = {"patient": patient.to_dict(), "ai_cached": from_cache}
    if ai_error:
        body["warning"] = f"Record saved, but the AI prediction failed: {ai_error}"
    return jsonify(body), status


def csv_safe(value):
    """Stop spreadsheet apps from running a cell as a formula (CSV injection)."""
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


def duplicate_response(duplicate):
    message = (
        f"A record for {duplicate.full_name} with the same date of birth and email "
        f"already exists (record #{duplicate.id})."
    )
    return jsonify(errors={"record": message}), 409


@api.errorhandler(404)
def not_found(_error):
    return jsonify(error="Patient record not found."), 404


@api.get("/patients")
def list_patients():
    patients = Patient.query.order_by(Patient.id).all()
    return jsonify(patients=[patient.to_dict() for patient in patients])


@api.get("/patients/export.csv")
def export_patients_csv():
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header for header, _key in CSV_COLUMNS)
    for patient in Patient.query.order_by(Patient.id):
        row = patient.to_dict()
        writer.writerow(csv_safe(row[key]) for _header, key in CSV_COLUMNS)

    filename = f"patients_{date.today():%Y-%m-%d}.csv"
    return Response(
        # The BOM makes Excel open the file as UTF-8
        "﻿" + buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@api.get("/patients/<int:patient_id>")
def get_patient(patient_id):
    return jsonify(patient=db.get_or_404(Patient, patient_id).to_dict())


@api.post("/patients")
def create_patient():
    cleaned, errors = validate_patient(request.get_json(silent=True) or {})
    if errors:
        return jsonify(errors=errors), 400

    duplicate = find_duplicate(cleaned)
    if duplicate:
        return duplicate_response(duplicate)

    patient = Patient(**cleaned)
    ai_error, from_cache = apply_ai_prediction(patient)
    db.session.add(patient)
    db.session.commit()
    return saved_response(patient, ai_error, from_cache, 201)


@api.put("/patients/<int:patient_id>")
def update_patient(patient_id):
    patient = db.get_or_404(Patient, patient_id)

    cleaned, errors = validate_patient(request.get_json(silent=True) or {})
    if errors:
        return jsonify(errors=errors), 400

    duplicate = find_duplicate(cleaned, exclude_id=patient.id)
    if duplicate:
        return duplicate_response(duplicate)

    needs_prediction = patient.risk_level is None or any(
        getattr(patient, field) != cleaned[field] for field in AI_INPUT_FIELDS
    )
    for field, value in cleaned.items():
        setattr(patient, field, value)

    ai_error, from_cache = apply_ai_prediction(patient) if needs_prediction else (None, False)
    db.session.commit()
    return saved_response(patient, ai_error, from_cache, 200)


@api.delete("/patients/<int:patient_id>")
def delete_patient(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    db.session.delete(patient)
    db.session.commit()
    return jsonify(message=f"Record #{patient_id} ({patient.full_name}) deleted.")


@api.post("/patients/<int:patient_id>/remarks")
def regenerate_remarks(patient_id):
    """Retry the AI prediction for a record, e.g. after the API was unavailable."""
    patient = db.get_or_404(Patient, patient_id)
    ai_error, _from_cache = apply_ai_prediction(patient)
    db.session.commit()
    if ai_error:
        return jsonify(error=f"AI prediction failed: {ai_error}", patient=patient.to_dict()), 502
    return jsonify(patient=patient.to_dict())
