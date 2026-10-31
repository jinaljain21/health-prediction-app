from datetime import date

from flask import Flask, render_template

from ai_service import calculate_age
from config import Config
from models import Patient, db
from rate_limiter import RateLimiter
from reference_ranges import REFERENCE_RANGES
from routes import api
from validators import BLOOD_TESTS


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    app.extensions["ai_rate_limiter"] = RateLimiter(app.config["AI_CALLS_PER_MINUTE"])
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return render_template("index.html", reference_ranges=REFERENCE_RANGES)

    @app.get("/patients/<int:patient_id>/report")
    def patient_report(patient_id):
        patient = db.get_or_404(Patient, patient_id)
        return render_template(
            "report.html",
            patient=patient.to_dict(),
            age=calculate_age(patient.date_of_birth),
            reference_ranges=REFERENCE_RANGES,
            units={field: unit for field, (_label, _min, _max, unit) in BLOOD_TESTS.items()},
            report_date=date.today().strftime("%d/%m/%Y"),
        )

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    create_app().run()
