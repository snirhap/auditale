from datetime import datetime, timedelta, timezone
from random import random, choice, randint
from faker import Faker
from sqlalchemy import text
from app import create_app
from app.config import Config
from app.models import ApiUsage, Invoice, SupportTicket, db, Customer, LoginEvent, FeatureUsage

fake = Faker()

TRUNCATE_FIRST = True

NEW_CUSTOMERS = 10
DAYS_HISTORY = 90
MAX_LOGINS_PER_CUSTOMER = 15
MAX_FEATURES_PER_CUSTOMER = 20
MAX_CUSTOMER_TICKETS = 5
MAX_CUSTOMER_INVOICES = 5
MAX_API_CALLS = 50
FEATURE_NAMES = ["Dashboard", "Reports", "Messages", "Notifications", "Documentation"]
SEGMENTS = ["Enterprise", "SMB", "Startup", "Bootstrap", "Private"]
API_ENDPOINTS = ["login", "register", "get_report", "update_profile", "fetch_data", "graphs", "alerts"]

def random_date_within_3_months():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS_HISTORY)
    return start + (end - start) * random()

def seed():
    app = create_app(Config)

    with app.app_context():

        if TRUNCATE_FIRST:
            with db.engine.begin() as conn:  # use a transaction
                truncate_stmt = "TRUNCATE TABLE {} RESTART IDENTITY CASCADE;".format(
                    ", ".join([t.name for t in db.metadata.sorted_tables])
                )
                conn.execute(text(truncate_stmt))
    
        with app.db_manager.get_write_session() as session:
            customers = []
            for _ in range(NEW_CUSTOMERS):
                customer = Customer(name=fake.company(), segment=choice(SEGMENTS))
                session.add(customer)
                customers.append(customer)

            session.commit()  # ensures customers get IDs

            # Add login events, feature usage, support tickets, invoices and api usage for each customer
            for customer in customers:
                # Logins
                for _ in range(randint(0, MAX_LOGINS_PER_CUSTOMER)):
                    login = LoginEvent(
                        customer_id=customer.id,
                        timestamp=random_date_within_3_months()
                    )
                    session.add(login)

                # Features access
                for _ in range(randint(0, MAX_FEATURES_PER_CUSTOMER)):
                    feature = FeatureUsage(
                        customer_id=customer.id,
                        feature_name=choice(FEATURE_NAMES),
                        timestamp=random_date_within_3_months()
                    )
                    session.add(feature)

                # Tickets
                for _ in range(randint(0, MAX_CUSTOMER_TICKETS)):
                    ticket_status = choice(['open','closed'])
                    ticket_created_at = random_date_within_3_months()

                    if ticket_status == 'closed':
                        max_seconds = int((datetime.now(timezone.utc) - ticket_created_at).total_seconds())
                        tickets_closed_at = ticket_created_at + timedelta(seconds=randint(1, max_seconds))
                    else:
                        tickets_closed_at = None

                    ticket = SupportTicket(
                        customer_id=customer.id,
                        status=ticket_status,
                        created_at=ticket_created_at,
                        closed_at=tickets_closed_at
                    )
                    session.add(ticket)
                
                # Invoices
                for _ in range(randint(0, MAX_CUSTOMER_INVOICES)):
                    invoice_status = choice(['unpaid', 'paid', 'late'])
                    invoice_due_date = random_date_within_3_months()
                    invoice_amount = fake.pyfloat(min_value=1, max_value=1000)

                    if invoice_status in ['paid', 'late']:
                        max_seconds = int((datetime.now(timezone.utc) - invoice_due_date).total_seconds())
                        invoice_paid_date = invoice_due_date + timedelta(seconds=randint(0, max_seconds)) if invoice_status == 'late' else invoice_due_date - timedelta(seconds=randint(0, max_seconds))
                    else:
                        invoice_paid_date = None

                    invoice = Invoice(
                        customer_id=customer.id,
                        status=invoice_status,
                        due_date=invoice_due_date,
                        amount=invoice_amount,
                        paid_date=invoice_paid_date
                    )
                    session.add(invoice)
                
                for _ in range(randint(0, MAX_API_CALLS)):
                    usage = ApiUsage(
                        customer_id=customer.id,
                        timestamp=random_date_within_3_months(),
                        api_endpoint=choice(API_ENDPOINTS)
                    )
                    session.add(usage)

            print("Seeding complete.")

if __name__ == "__main__":
    seed()