from flask import Flask, render_template

from config import Config
from models import db
from reference_ranges import REFERENCE_RANGES
from routes import api


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return render_template("index.html", reference_ranges=REFERENCE_RANGES)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    create_app().run()
