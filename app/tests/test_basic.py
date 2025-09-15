from datetime import datetime, timedelta, timezone
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

def test_add_customer_event(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Event Test Customer", segment="Startup")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    # Add a login event
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "login",
        "timestamp": datetime.now().isoformat()
    }, follow_redirects=True)

    assert b'event recorded successfully' in response.data

    # Add an invalid event type
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "invalid_event",
        "timestamp": datetime.now().isoformat()
    }, follow_redirects=True)

    assert b'Unknown event type' in response.data

    # Test for non-existing customer
    response = client.post('/customers/99999/events', json={
        "event_type": "login",
        "timestamp": datetime.now().isoformat()
    }, follow_redirects=True)

    assert b'Customer does not exist' in response.data


def test_invalid_timestamp(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Timestamp Test Customer", segment="SMB")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    # Add a login event with invalid timestamp
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "login",
        "timestamp": "invalid-timestamp"
    }, follow_redirects=True)

    assert b"Invalid data format" in response.data

def test_customers_page_content(client):
    response = client.get('/customers')
    assert response.status_code == 200
    assert b'<table' in response.data  # Check if a table is present
    assert b'<th' in response.data     # Check if table headers are present
    assert b'<td' in response.data     # Check if table data cells are present

def test_dashboard_page_content(client):
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Latest Logins' in response.data  # Check for latest logins section
    assert b'Latest Feature Usages' in response.data  # Check for latest features section
    assert b'Latest Invoices' in response.data  # Check for latest invoices section
    assert b'At-Risk Customers' in response.data  # Check for risky customers section

def test_customer_health_page_content(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Health Content Test Customer", segment="Enterprise")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    response = client.get(f'/customers/{customer_id}/health')
    assert response.status_code == 200
    assert b'Health Breakdown' in response.data  # Check for customer health section
    assert b'Overall Health Score' in response.data     # Check for health score presence

def test_customer_detail_page_content(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Detail Content Test Customer", segment="Startup")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    response = client.get(f'/customers/{customer_id}')
    assert response.status_code == 200
    assert b'Customer Details' in response.data  # Check for customer details section
    assert b'Detail Content Test Customer' in response.data  # Check for customer name presence

def test_add_feature_event_missing_field(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Feature Event Test Customer", segment="SMB")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    # Add a feature event without feature_name
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "feature",
        "timestamp": datetime.now().isoformat()
    }, follow_redirects=True)

    assert b'Feature name and timestamp are required for feature event.' in response.data

def test_add_feature_event_success(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Feature Event Success Test Customer", segment="Enterprise")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    # Add a feature event with all required fields
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "feature",
        "feature_name": "Advanced Analytics",
        "timestamp": datetime.now().isoformat()
    }, follow_redirects=True)

    assert b'event recorded' in response.data

def test_add_ticket_event_success(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Ticket Event Success Test Customer", segment="Startup")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    # Add a ticket event with all required fields
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "ticket",
        "status": "open",
        "created_at": datetime.now().isoformat()
    }, follow_redirects=True)

    assert b'event recorded successfully' in response.data

def test_add_invoice_event_success(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Invoice Event Success Test Customer", segment="Enterprise")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    # Add an invoice event with all required fields
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "invoice",
        "issued_at": (datetime.now() - timedelta(days=30)).isoformat(),
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "amount": 1500.00,
        "status": "paid",
        "paid_date": (datetime.now() - timedelta(days=15)).isoformat()
    }, follow_redirects=True)

    assert b'event recorded' in response.data

def test_risky_customers_in_dashboard(client):
    # Create a customer with low health score to ensure they appear in risky customers
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer, SupportTicket
        new_customer = Customer(name="Risky Customer", segment="SMB")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

        # Add multiple open support tickets to lower health score
        for _ in range(5):
            ticket = SupportTicket(customer_id=customer_id, status="open", created_at=datetime.now(timezone.utc))
            session.add(ticket)
        session.commit()

        # Add unpaid invoices to further lower health score
        from app.models import Invoice
        for _ in range(3):
            invoice = Invoice(customer_id=customer_id,
                              issued_at=datetime.now(timezone.utc) - timedelta(days=60),
                              due_date=datetime.now(timezone.utc) - timedelta(days=30),
                              amount=500.00,
                              status="unpaid")
            session.add(invoice)
        session.commit()

    response = client.get('/dashboard')

    assert response.status_code == 200

    assert b'At-Risk Customers' in response.data  # Check for risky customers section
    assert b'<td>Risky Customer</td>'  in response.data  # Ensure non-risky customers are not listed
    assert b'<td>0.0</td>' in response.data  # Check for health score presence

def test_future_timestamp_event(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Future Timestamp Test Customer", segment="SMB")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    future_time = (datetime.now() + timedelta(days=1)).isoformat()

    # Add a login event with a future timestamp
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "login",
        "timestamp": future_time
    }, follow_redirects=True)

    assert b"Timestamp cannot be in the future" in response.data

def test_invoice_event_invalid_dates(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Invoice Date Test Customer", segment="Enterprise")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    issued_at = (datetime.now() + timedelta(days=1)).isoformat()  # Future date
    due_date = (datetime.now() - timedelta(days=10)).isoformat()   # Past date

    # Add an invoice event with issued_at in the future and due_date before issued_at
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "invoice",
        "issued_at": issued_at,
        "due_date": due_date,
        "amount": 1000.00
    }, follow_redirects=True)

    assert b"issued_at cannot be in the future" in response.data

def test_invoice_event_due_date_before_issued_at(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Invoice Due Date Test Customer", segment="Enterprise")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    issued_at = (datetime.now() - timedelta(days=5)).isoformat()  # Past date
    due_date = (datetime.now() - timedelta(days=10)).isoformat()   # Earlier past date

    # Add an invoice event with due_date before issued_at
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "invoice",
        "issued_at": issued_at,
        "due_date": due_date,
        "amount": 1000.00
    }, follow_redirects=True)

    assert b"due_date cannot be before issued_at" in response.data

def test_invoice_event_negative_amount(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Invoice Negative Amount Test Customer", segment="SMB")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    issued_at = (datetime.now() - timedelta(days=5)).isoformat()  # Past date
    due_date = (datetime.now() + timedelta(days=5)).isoformat()   # Future date

    # Add an invoice event with negative amount
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "invoice",
        "issued_at": issued_at,
        "due_date": due_date,
        "amount": -500.00
    }, follow_redirects=True)

    assert b"Amount must be positive" in response.data

def test_invoice_event_invalid_amount_format(client):
    # First, create a customer to ensure one exists
    with current_app.db_manager.get_write_session() as session:
        from app.models import Customer
        new_customer = Customer(name="Invoice Invalid Amount Test Customer", segment="Enterprise")
        session.add(new_customer)
        session.commit()
        customer_id = new_customer.id

    issued_at = (datetime.now() - timedelta(days=5)).isoformat()  # Past date
    due_date = (datetime.now() + timedelta(days=5)).isoformat()   # Future date

    # Add an invoice event with invalid amount format
    response = client.post(f'/customers/{customer_id}/events', json={
        "event_type": "invoice",
        "issued_at": issued_at,
        "due_date": due_date,
        "amount": "invalid_amount"
    }, follow_redirects=True)

    assert b"Amount must be a valid number" in response.data