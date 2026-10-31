# Health Risk Predictor - AI Health Prediction from Blood Test Results

[![Tests](https://github.com/jinaljain21/health-prediction-app/actions/workflows/tests.yml/badge.svg)](https://github.com/jinaljain21/health-prediction-app/actions/workflows/tests.yml)

A web application, built with Python, Flask and Google Gemini, that stores patient blood test results and predicts possible health risks. Every record is validated before it is saved, and Gemini writes a short remark explaining the likely risk (for example diabetes, anaemia or high cholesterol), shown in the Remarks column.

**Live demo:** https://health-risk-predictor-hgqu.onrender.com
(Hosted on Render's free plan: the first visit can take up to a minute to wake up, and data may reset.)

## Features

### Patient Records (CRUD)
- Add, view, edit and delete patient records
- Each record stores Full Name, Date of Birth, Email, Glucose, Haemoglobin, Cholesterol and the AI Remarks
- Records are saved in an SQLite database, so they are kept after the app is closed

### Data Validation
- Full name: required, 2-100 characters, letters, spaces, apostrophes, dots and hyphens only
- Date of birth: dd/mm/yyyy format (dots or dashes are also accepted, for example 28.01.1960), must be a real calendar date (31/11 is rejected), cannot be in the future
- Email: must have exactly one "@" and a domain extension such as ".com"
- Glucose, Haemoglobin and Cholesterol: must be numeric and within realistic limits
- Duplicates: the same name, date of birth and email cannot be added twice
- All errors are checked on the server and shown under the matching field, all at once

### AI Health Prediction
- Gemini receives the patient's age and three blood values and returns a risk level (Low, Moderate or High) with a short remark
- Gemini is asked for structured JSON output, so the answer is always parsed reliably
- Only the age and blood values are sent to the AI, never the name or email
- If the AI is unavailable (no key, timeout, quota reached), the record is still saved and can be retried with one click
- When a record is edited, the AI is only called again if the date of birth or a blood value changed
- AI answers are cached: if the same age and blood values were analysed before, the saved answer is reused instantly with no API call
- A rate limit (10 AI calls per minute by default) protects the API quota on the public demo

### Patient Report
- One-page health report for each patient: details, age, each result against its normal range, and the AI assessment
- Print it or save it as a PDF directly from the browser

### Dashboard
- Summary cards showing total patients and the number at High, Moderate and Low risk; click a card to filter the table
- Blood values outside the normal adult range are highlighted (red ↑ high, blue ↓ low)
- Search by name or email
- Export all records to CSV (protected against spreadsheet formula injection)
- Light and dark mode, remembered between visits

### Testing
- 57 automated tests, including all 10 records from the assignment
- GitHub Actions runs the tests automatically on every push

## Tech Stack
- Python 3.12
- Flask (web framework and REST API)
- SQLite with Flask-SQLAlchemy (database)
- Google Gemini API (AI health prediction)
- Requests (calling the Gemini API)
- HTML, Bootstrap 5 and JavaScript (frontend)
- pytest (automated tests)
- GitHub Actions (continuous integration)
- Gunicorn and Render (production server and hosting)
- Claude Code (AI pair programmer used to build the project)

## Project Structure
```
app.py                  starts the app and connects all the parts
config.py               settings loaded from the .env file
models.py               the patient database table
validators.py           checks every field before saving
ai_service.py           Gemini API connection and prompt
reference_ranges.py     normal ranges used to highlight abnormal values
rate_limiter.py         limits AI calls per minute
routes.py               REST API (create, read, update, delete, AI retry, CSV export)
templates/index.html    the main web page
templates/report.html   the printable patient report
static/js/app.js        sends data to the API and updates the page
static/js/theme.js      light / dark mode toggle
static/css/style.css    page styling
tests/                  automated tests
.github/workflows/      GitHub Actions test pipeline
render.yaml             Render deployment settings
.env.example            example settings (no real keys)
```

## REST API
- `GET /api/patients` - list all records
- `GET /api/patients/<id>` - get one record
- `POST /api/patients` - validate, predict and save a new record
- `PUT /api/patients/<id>` - validate and update a record
- `DELETE /api/patients/<id>` - delete a record
- `POST /api/patients/<id>/remarks` - run the AI prediction again
- `GET /api/patients/export.csv` - download all records as CSV

Validation errors return HTTP 400, duplicates return HTTP 409, and missing records return HTTP 404.

The printable report for a patient is at `/patients/<id>/report`.

## How to Run Locally
1. Install Python 3.12.
2. Open a terminal in the project folder and create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install the required libraries:
   ```
   pip install -r requirements.txt
   ```
4. Get a free Gemini API key from https://aistudio.google.com/apikey.
5. Copy `.env.example` to `.env` and add your key:
   ```
   GEMINI_API_KEY=your-key
   ```
6. Start the app:
   ```
   python app.py
   ```
7. Open http://127.0.0.1:5000 in your browser.

To run the automated tests (no API key needed, the AI is replaced with a test version):
```
pytest
```

Note: the free Gemini plan allows a limited number of requests per day.

## Deployment
The app is set up for Render using `render.yaml`:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn "app:create_app()"` (a production server instead of Flask's development server)
- The Gemini API key is entered as an environment variable in the Render dashboard, never stored in the code
- Every push to GitHub redeploys the app automatically

On the free plan the app sleeps after 15 minutes without visitors (the first visit then takes up to a minute), and the SQLite data resets when the app restarts. A production setup would use a managed database such as PostgreSQL by changing `DATABASE_URL`.

## Test Data Results
The 10 records from the assignment give these results:
- Records 1, 3, 5, 7, 9 and 10 are saved with an AI prediction
- Record 2 (John Hunter) is rejected: the email `hunter@gmail` has no domain extension
- Record 4 (Peter Larry) is rejected: `31.11.2001` is not a real date, as November has only 30 days
- Record 6 (Robyn Pears) is rejected: it is a duplicate of record 1
- Record 8 (Kris Wu) is rejected: the email `Kris.wu.gmail.com` has no "@", and `19.10.2030` is in the future

## Disclaimer
The predictions are generated by AI for demonstration purposes and are not a medical diagnosis.

## Author
Jinal Jain
