from datetime import date

import pytest

from validators import (
    validate_blood_value,
    validate_date_of_birth,
    validate_email,
    validate_full_name,
    validate_patient,
)

TODAY = date(2026, 10, 30)


@pytest.mark.parametrize("text", ["28/01/1960", "28.01.1960", "28-01-1960"])
def test_date_accepts_common_separators(text):
    assert validate_date_of_birth(text, today=TODAY) == date(1960, 1, 28)


@pytest.mark.parametrize(
    "text, message",
    [
        ("", "required"),
        ("1960-01-28", "dd/mm/yyyy"),
        ("28/01.1960", "dd/mm/yyyy"),
        ("31.11.2001", "November 2001 has only 30 days"),
        ("29/02/2023", "February 2023 has only 28 days"),
        ("12/13/1990", "month must be between 01 and 12"),
        ("19.10.2030", "cannot be in the future"),
        ("01/01/1890", "more than 120 years"),
    ],
)
def test_date_rejects_invalid_values(text, message):
    with pytest.raises(ValueError, match=message):
        validate_date_of_birth(text, today=TODAY)


def test_date_accepts_leap_day():
    assert validate_date_of_birth("29/02/2024", today=TODAY) == date(2024, 2, 29)


@pytest.mark.parametrize("email", ["robyn@gmail.com", "timd@smh.com.au", "Larry@hotmail.com"])
def test_email_accepts_valid_addresses(email):
    assert validate_email(email) == email


@pytest.mark.parametrize(
    "email, message",
    [
        ("", "required"),
        ("hunter@gmail", "missing an extension"),
        ("Kris.wu.gmail.com", "exactly one '@'"),
        ("a@@b.com", "exactly one '@'"),
        ("name with space@mail.com", "not in a valid format"),
    ],
)
def test_email_rejects_invalid_addresses(email, message):
    with pytest.raises(ValueError, match=message):
        validate_email(email)


def test_full_name_collapses_extra_spaces():
    assert validate_full_name("  Robyn   Pears ") == "Robyn Pears"


@pytest.mark.parametrize("name", ["", "A", "R2D2"])
def test_full_name_rejects_invalid_names(name):
    with pytest.raises(ValueError):
        validate_full_name(name)


@pytest.mark.parametrize("value, expected", [("13.5", 13.5), (15, 15.0), (" 7.6 ", 7.6)])
def test_blood_value_accepts_numbers(value, expected):
    assert validate_blood_value("haemoglobin", value) == expected


@pytest.mark.parametrize(
    "value, message",
    [("", "required"), ("abc", "numeric"), ("nan", "numeric"), ("-5", "between"), ("5000", "between")],
)
def test_blood_value_rejects_invalid_values(value, message):
    with pytest.raises(ValueError, match=message):
        validate_blood_value("glucose", value)


def test_validate_patient_reports_every_invalid_field():
    _cleaned, errors = validate_patient({"full_name": "Kris Wu", "date_of_birth": "19.10.2030",
                                         "email": "Kris.wu.gmail.com", "glucose": "79",
                                         "haemoglobin": "16.5", "cholesterol": "197"})
    assert set(errors) == {"date_of_birth", "email"}
