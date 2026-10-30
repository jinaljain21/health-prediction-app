"""Health-risk prediction using the Google Gemini REST API.

Only the patient's age and blood test values are sent to the API.
Name and email never leave the application.
"""
import json
from datetime import date

import requests

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RISK_LEVELS = ("Low", "Moderate", "High")

# Ask Gemini to answer in a fixed JSON shape so the reply can be parsed reliably
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "risk_level": {"type": "STRING"},
        "remarks": {"type": "STRING"},
    },
    "required": ["risk_level", "remarks"],
}


class AIServiceError(Exception):
    """Raised when a prediction could not be obtained from the AI API."""


def calculate_age(date_of_birth, today=None):
    today = today or date.today()
    had_birthday = (today.month, today.day) >= (date_of_birth.month, date_of_birth.day)
    return today.year - date_of_birth.year - (0 if had_birthday else 1)


def build_prompt(age, glucose, haemoglobin, cholesterol):
    return (
        "You are a clinical decision-support assistant reviewing blood test results.\n\n"
        f"Patient age: {age} years (sex not recorded)\n"
        f"Blood glucose: {glucose} mg/dL\n"
        f"Haemoglobin: {haemoglobin} g/dL\n"
        f"Total cholesterol: {cholesterol} mg/dL\n\n"
        "Compare each value with standard adult reference ranges and identify the most likely "
        "health conditions or disease risks (for example diabetes, anaemia, polycythaemia, "
        "high cholesterol or cardiovascular disease).\n"
        "Respond with:\n"
        '- risk_level: exactly one of "Low", "Moderate" or "High"\n'
        "- remarks: one or two short sentences (max 40 words) naming the abnormal values and "
        "the possible condition. If all values are normal, say so.\n"
        "This is a screening aid, so do not give a diagnosis or treatment advice."
    )


def predict_health_risk(date_of_birth, glucose, haemoglobin, cholesterol, *, api_key, model, timeout=30):
    """Call Gemini and return {"risk_level": ..., "remarks": ...}. Raises AIServiceError on failure."""
    if not api_key:
        raise AIServiceError("GEMINI_API_KEY is not configured.")

    prompt = build_prompt(calculate_age(date_of_birth), glucose, haemoglobin, cholesterol)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }

    try:
        response = requests.post(
            GEMINI_ENDPOINT.format(model=model),
            headers={"x-goog-api-key": api_key},
            json=payload,
            timeout=timeout,
        )
    except requests.Timeout:
        raise AIServiceError("The AI service did not respond in time.") from None
    except requests.RequestException as exc:
        raise AIServiceError(f"Could not reach the AI service ({exc.__class__.__name__}).") from exc

    if not response.ok:
        raise AIServiceError(f"AI service returned HTTP {response.status_code}: {_error_message(response)}")

    try:
        body = response.json()
    except ValueError:
        raise AIServiceError("The AI service returned a response that is not JSON.") from None
    return _parse_prediction(body)


def _error_message(response):
    try:
        return response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return response.reason or "unknown error"


def _parse_prediction(body):
    block_reason = body.get("promptFeedback", {}).get("blockReason")
    if block_reason:
        raise AIServiceError(f"The AI service blocked the request ({block_reason}).")

    try:
        parts = body["candidates"][0]["content"]["parts"]
        result = json.loads("".join(part.get("text", "") for part in parts))
        risk_level = str(result["risk_level"]).strip().capitalize()
        remarks = str(result["remarks"]).strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AIServiceError("The AI service returned an unexpected response.") from exc

    if risk_level not in RISK_LEVELS or not remarks:
        raise AIServiceError("The AI service returned an incomplete prediction.")
    return {"risk_level": risk_level, "remarks": remarks}
