from flask import Flask, jsonify
from flask_migrate import Migrate
from .config import Config
from .models import db
from .db_manager import DatabaseManager

def create_app(config_obj):
    app = Flask(__name__)
    app.config.from_object(config_obj)

    db.init_app(app)
    
    migrate = Migrate(app, db)

    # Set up custom database manager for read/write session and engine handling
    app.db_manager = DatabaseManager(config_obj)

    @app.route('/')
    def home():
        return jsonify({"message": f"Welcome"})

    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp


    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    
    return app
