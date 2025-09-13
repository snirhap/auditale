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

def test_dashboard(client):
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Dashboard' in response.data

def test_customers_list(client):
    response = client.get('/customers')
    assert response.status_code == 200
    assert b'Customers' in response.data

def test_customer_detail(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Test Customer", segment="SMB")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    response = client.get(f'/customers/{customer_id}')
    assert response.status_code == 200
    assert b'Test Customer' in response.data

    # Test for non-existing customer
    response = client.get('/customers/99999')
    assert response.status_code == 404

def test_customer_health(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Health Test Customer", segment="Enterprise")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    response = client.get(f'/customers/{customer_id}/health')
    assert response.status_code == 200
    assert b'Health Test Customer' in response.data

    # Test for non-existing customer
    response = client.get('/customers/99999/health')
    assert response.status_code == 404