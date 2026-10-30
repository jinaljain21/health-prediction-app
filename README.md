# Health Risk Predictor

A web application that stores patient blood test results and uses the Google Gemini API to predict possible health risks.

Users can add, view, edit and delete patient records. Each record is validated on the server, saved to a database, and sent to Gemini, which returns a risk level (Low / Moderate / High) and a short remark that is shown in the **Remarks** column.

## Features

- Create, read, update and delete patient records
- Server-side validation with a clear message under each invalid field
- AI risk prediction (Google Gemini) shown in the Remarks column, with a retry option if the API is unavailable
- Summary cards with patient counts per risk level; click a card to filter the table
- Blood values outside the normal adult range are highlighted (↑ high, ↓ low)
- Search by name or email
- Export all records to a CSV file that opens in Excel
- Automated tests run on every push with GitHub Actions

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask (REST API) |
| Database | SQLite through Flask-SQLAlchemy (any SQLAlchemy-supported database can be used) |
| AI | Google Gemini `generateContent` REST API, called with `requests` |
| Frontend | HTML, Bootstrap 5, vanilla JavaScript (Fetch API) |
| Tests | pytest |

## Project structure

```
health-prediction-app/
├── app.py              # Creates the Flask app, registers routes, creates tables
├── config.py           # Settings loaded from environment variables / .env
├── models.py           # Patient database model
├── validators.py       # Server-side input validation
├── ai_service.py       # Gemini API integration (prompt, request, response parsing)
├── reference_ranges.py # Normal ranges used to flag abnormal blood values
├── routes.py           # REST API endpoints (CRUD, AI retry, CSV export)
├── templates/
│   └── index.html      # Single-page user interface
├── static/
│   ├── css/style.css
│   └── js/app.js       # Calls the API, renders the table, shows errors
├── tests/              # Unit and API tests (AI call is mocked)
├── .github/workflows/  # GitHub Actions: runs the tests on every push
├── .env.example        # Template for local configuration
└── requirements.txt
```

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # macOS / Linux
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your Gemini API key (free from [Google AI Studio](https://aistudio.google.com/apikey)):

   ```
   GEMINI_API_KEY=your-key-here
   ```

3. Start the application:

   ```bash
   python app.py
   ```

4. Open http://127.0.0.1:5000 in a browser.

The SQLite database is created automatically at `instance/health.db` on first run.

## How it works

1. The user fills in the form and clicks **Save & Predict**.
2. `app.js` sends the data as JSON to `POST /api/patients`.
3. `validators.py` checks every field and returns all errors at once (HTTP 400).
4. `routes.py` checks for a duplicate patient (same name, date of birth and email) and returns HTTP 409 if one exists.
5. `ai_service.py` sends the patient's **age and blood values only** (no name or email) to Gemini and asks for a JSON answer with `risk_level` and `remarks`.
6. The record is saved with the prediction and the table is refreshed.

If the AI service is unavailable (no key, timeout, quota exceeded), the record is still saved and the Remarks column shows the reason with a **Retry AI** button.

When a record is edited, a new prediction is only requested if the date of birth or a blood value changed. Changing just the name or email keeps the existing remark.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/patients` | List all records |
| GET | `/api/patients/<id>` | Get one record |
| GET | `/api/patients/export.csv` | Download all records as CSV |
| POST | `/api/patients` | Validate, predict and create a record |
| PUT | `/api/patients/<id>` | Validate and update a record |
| DELETE | `/api/patients/<id>` | Delete a record |
| POST | `/api/patients/<id>/remarks` | Re-run the AI prediction for a record |

Validation errors are returned as `{"errors": {"field": "message"}}`.

## Validation rules

| Field | Rule |
|---|---|
| Full Name | Required, 2–100 characters, letters, spaces, `.` `'` `-` only |
| Date of Birth | `dd/mm/yyyy` (`.` or `-` separators also accepted), must be a real calendar date, not in the future, not more than 120 years ago |
| Email | Exactly one `@`, a domain with an extension (e.g. `.com`), valid characters |
| Glucose | Numeric, 20–1000 mg/dL |
| Haemoglobin | Numeric, 1–25 g/dL |
| Cholesterol | Numeric, 50–1000 mg/dL |
| Record | Same name + date of birth + email cannot be added twice |

The numeric limits reject impossible values (typos). Abnormal but realistic results are accepted and assessed by the AI.

## Abnormal value highlighting

Each record returned by the API includes `flags`, calculated in `reference_ranges.py`:

| Test | Normal adult range |
|---|---|
| Glucose | 70–140 mg/dL (non-fasting) |
| Haemoglobin | 12–17.5 g/dL (sex not recorded, so the combined adult range is used) |
| Cholesterol | below 200 mg/dL |

The table marks values above the range in red (↑) and below it in blue (↓). This rule-based check is instant and predictable, while the AI remark explains what the combination of values may mean.

## Test data results

| # | Name | Result | Reason |
|---|---|---|---|
| 1 | Robyn Pears | Saved | |
| 2 | John Hunter | Rejected | `hunter@gmail` has no domain extension |
| 3 | Darryl Tim | Saved | |
| 4 | Peter Larry | Rejected | `31.11.2001`: November has only 30 days |
| 5 | Sam Kerr | Saved | |
| 6 | Robyn Pears | Rejected | Duplicate of record 1 |
| 7 | Madison XI | Saved | |
| 8 | Kris Wu | Rejected | `Kris.wu.gmail.com` has no `@`, and `19.10.2030` is in the future |
| 9 | Tenille Singh | Saved | |
| 10 | Prem Kumar | Saved | |

## Running tests

```bash
pytest
```

The tests replace the Gemini call with a fake prediction, so they run offline and do not need an API key. They include all ten records from the assignment and check that exactly records 2, 4, 6 and 8 are rejected, for the expected reasons.

GitHub Actions (`.github/workflows/tests.yml`) runs the same tests automatically on every push and pull request.

## Disclaimer

Predictions are generated by an AI model for demonstration purposes and are not a medical diagnosis.
