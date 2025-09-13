import os
from app import create_app, db
from app.config import Config, TestConfig
from utils.seed_db import seed

env = os.getenv("FLASK_ENV", "development")  # "development", "testing", "production"

if env == "testing":
    app = create_app(TestConfig)
    with app.app_context():
        # create tables
        from app.models import db
        db.create_all()
        # seed data
        seed(app)
elif env == "development":
    app = create_app(Config)
    with app.app_context():
        # seed data
        seed(app)
else:
    app = create_app(Config)

if __name__ == "__main__":
    debug_mode = True if env != "production" else False
    # Run app on all interfaces for dev/testing if needed
    app.run(debug=debug_mode, host="0.0.0.0", port=int(os.getenv("APP_PORT", 8000)))