import os
import random
from flask import Flask, current_app
import pytest
from app import create_app
from app.models import db
from app.config import TestConfig

TEST_DB = TestConfig.TEST_DB

@pytest.fixture(scope='session')
def app():
    app = create_app(config_obj=TestConfig)
    db_manager = app.db_manager

    with app.app_context():
        db.metadata.create_all(bind=db_manager.write_engine)

    yield app

    # Clean up
    with app.app_context():
        db.metadata.drop_all(bind=db_manager.write_engine)
        db.session.remove()
        db_manager.write_engine.dispose()
        if os.path.exists(TestConfig.TEST_DB):
            os.remove(TestConfig.TEST_DB)

@pytest.fixture(scope='session')
def client(app: Flask):
    with app.app_context():
        with app.test_client() as client:
            yield client

def test_basic(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.get_json() == {'message': 'Welcome'}
