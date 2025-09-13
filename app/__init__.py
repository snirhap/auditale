from flask import Flask, redirect, url_for
from flask_migrate import Migrate
from .models import db
from .db_manager import DatabaseManager

def create_app(config_obj):
    app = Flask(__name__)
    app.config.from_object(config_obj)

    db.init_app(app)
    
    Migrate(app, db) # enables db migrations/metadata updates

    # Set up custom database manager for read/write session and engine handling
    app.db_manager = DatabaseManager(config_obj)

    @app.route('/')
    def root():
        return redirect(url_for('dashboard.dashboard'))

    from app.routes.customer import customer_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(customer_bp)
    app.register_blueprint(dashboard_bp)

    return app
