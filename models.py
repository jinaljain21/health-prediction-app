from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

from reference_ranges import flag_results

db = SQLAlchemy()

DATE_FORMAT = "%d/%m/%Y"


def utc_now():
    return datetime.now(timezone.utc)


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(254), nullable=False)
    glucose = db.Column(db.Float, nullable=False)  # mg/dL
    haemoglobin = db.Column(db.Float, nullable=False)  # g/dL
    cholesterol = db.Column(db.Float, nullable=False)  # mg/dL

    # Filled in by the AI service; risk_level stays empty if the AI call failed
    risk_level = db.Column(db.String(20))
    remarks = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.strftime(DATE_FORMAT),
            "email": self.email,
            "glucose": self.glucose,
            "haemoglobin": self.haemoglobin,
            "cholesterol": self.cholesterol,
            "flags": flag_results(self),
            "risk_level": self.risk_level,
            "remarks": self.remarks,
        }
