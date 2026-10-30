"""Adult reference ranges used to flag abnormal blood test results in the UI.

Sex is not recorded, so haemoglobin uses the combined adult range, and glucose
uses the non-fasting upper limit because the test type is not recorded either.
"""

# field: (lowest normal value, highest normal value, label shown in the legend)
REFERENCE_RANGES = {
    "glucose": (70, 140, "70–140 mg/dL"),
    "haemoglobin": (12.0, 17.5, "12–17.5 g/dL"),
    "cholesterol": (0, 199, "below 200 mg/dL"),
}


def classify(field, value):
    low, high, _label = REFERENCE_RANGES[field]
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "normal"


def flag_results(patient):
    """Return e.g. {"glucose": "high", "haemoglobin": "normal", "cholesterol": "normal"}."""
    return {field: classify(field, getattr(patient, field)) for field in REFERENCE_RANGES}
