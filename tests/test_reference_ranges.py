import pytest

from reference_ranges import classify


@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("glucose", 232, "high"),
        ("glucose", 94, "normal"),
        ("glucose", 65, "low"),
        ("haemoglobin", 7.6, "low"),
        ("haemoglobin", 13.5, "normal"),
        ("haemoglobin", 18.6, "high"),
        ("cholesterol", 180, "normal"),
        ("cholesterol", 199, "normal"),
        ("cholesterol", 200, "high"),
    ],
)
def test_classify(field, value, expected):
    assert classify(field, value) == expected
