"""Server-side validation for patient records.

Every validator returns the cleaned value or raises ValueError with a message
that is shown to the user next to the matching form field.
"""
import calendar
import math
import re
from datetime import date
from functools import partial

# dd/mm/yyyy. "." and "-" are accepted as separators too, but the same one must be used twice.
DATE_PATTERN = re.compile(r"^(\d{1,2})([/.\-])(\d{1,2})\2(\d{4})$")
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z .'\-]*$")
EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$"
)

MAX_AGE_YEARS = 120

# field: (label, minimum, maximum, unit) - wide limits that reject typos, not abnormal results
BLOOD_TESTS = {
    "glucose": ("Glucose", 20, 1000, "mg/dL"),
    "haemoglobin": ("Haemoglobin", 1, 25, "g/dL"),
    "cholesterol": ("Cholesterol", 50, 1000, "mg/dL"),
}


def validate_full_name(value):
    name = " ".join(str(value or "").split())
    if not name:
        raise ValueError("Full name is required.")
    if not 2 <= len(name) <= 100:
        raise ValueError("Full name must be between 2 and 100 characters.")
    if not NAME_PATTERN.match(name):
        raise ValueError(
            "Full name can only contain letters, spaces, apostrophes, dots and hyphens."
        )
    return name


def validate_date_of_birth(value, today=None):
    text = str(value or "").strip()
    if not text:
        raise ValueError("Date of birth is required.")

    match = DATE_PATTERN.match(text)
    if not match:
        raise ValueError("Date of birth must be in dd/mm/yyyy format.")

    day, month, year = int(match.group(1)), int(match.group(3)), int(match.group(4))
    if not 1 <= month <= 12:
        raise ValueError(f"'{text}' is not a valid date: month must be between 01 and 12.")

    days_in_month = calendar.monthrange(year, month)[1]
    if not 1 <= day <= days_in_month:
        raise ValueError(
            f"'{text}' is not a valid date: {calendar.month_name[month]} {year} "
            f"has only {days_in_month} days."
        )

    dob = date(year, month, day)
    today = today or date.today()
    if dob > today:
        raise ValueError("Date of birth cannot be in the future.")
    if today.year - dob.year > MAX_AGE_YEARS:
        raise ValueError(f"Date of birth cannot be more than {MAX_AGE_YEARS} years ago.")
    return dob


def validate_email(value):
    email = str(value or "").strip()
    if not email:
        raise ValueError("Email address is required.")
    if len(email) > 254:
        raise ValueError("Email address is too long.")
    if email.count("@") != 1:
        raise ValueError("Email address must contain exactly one '@' symbol.")

    domain = email.split("@")[1]
    if "." not in domain:
        raise ValueError(
            f"Email domain '{domain}' is incomplete: it is missing an extension such as '.com'."
        )
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Email address is not in a valid format (e.g. name@example.com).")
    return email


def validate_blood_value(field, value):
    label, minimum, maximum, unit = BLOOD_TESTS[field]
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValueError(f"{label} is required.")

    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"{label} must be a numeric value.") from None
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a numeric value.")

    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum} {unit}.")
    return number


FIELD_VALIDATORS = {
    "full_name": validate_full_name,
    "date_of_birth": validate_date_of_birth,
    "email": validate_email,
    **{field: partial(validate_blood_value, field) for field in BLOOD_TESTS},
}


def validate_patient(data):
    """Validate every field and collect all errors, so the user can fix them in one go."""
    cleaned, errors = {}, {}
    for field, validator in FIELD_VALIDATORS.items():
        try:
            cleaned[field] = validator(data.get(field))
        except ValueError as exc:
            errors[field] = str(exc)
    return cleaned, errors
