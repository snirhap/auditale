# Auditale

Auditale is a Flask-based application for tracking **customer activity events** (logins, invoices, support tickets, feature usage, API usage), computing **health scores**, and presenting dashboards and alerts for **customers at risk**.

---

## Features

- Record various types of events for customers:
  - **Login**
  - **Invoice**
  - **Ticket**
  - **API call**
  - **Feature usage**
- Compute a **health score** for each customer based on:
  - Login frequency
  - Invoice timeliness
  - Support tickets
  - Feature/API usage
- Dashboards:
  - Latest events (logins, tickets, invoices, etc.)
  - At-risk customers (with signals/alerts)
  - Customer details pages with event history
- Supports both **API usage** (JSON) and **form-based UI** (HTML) with validation & feedback
- Configurable for local SQLite, testing, or production Postgres (via Docker)

---

## Getting Started

### Prerequisites
- Python 3.9+
- Docker & Docker Compose (for Postgres and services)
- Git

### Local Development (SQLite)
```bash
git clone https://github.com/snirhap/auditale.git
cd auditale

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export FLASK_ENV=testing
python run.py
```

Then access to dashboard via:
```
http://127.0.0.1:8000/
```

This will use SQLite and auto-create the test DB.

### Docker Compose (Postgres with Write+Read DB Engines, nginex as Load balancer)
```
docker-compose up --build --scale web=3
```

Then access via:
```
http://0.0.0.0:80/dashboard
```

- Run migrations inside the container to set up schema:

```
docker-compose exec web flask db upgrade
```

## Configuration
* Config: default (Postgres, production/dev)

* TestConfig: SQLite, testing mode

* ```SECRET_KEY``` must be set for flash messages & sessions

Use .env or environment variables to configure Postgres credentials.

Example:
```
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=mysupersecretkey
APP_PORT=8000
POSTGRESQL_USERNAME=postgres
POSTGRESQL_PASSWORD=postgres
POSTGRESQL_DATABASE=auditale_db
POSTGRESQL_REPLICATION_USER=replica_user
POSTGRESQL_REPLICATION_PASSWORD=replica_pass
POSTGRESQL_PORT_NUMBER=5432
POSTGRESQL_MASTER_HOST=primary-db
POSTGRES_REPLICA_HOST=read-replica
READING_REPLICAS=2
```

## Database & Migrations
Create migrations when models change:
```
flask db migrate -m "Some change in DB models/schema"
flask db upgrade
```

### Seed test/fake data:

I build a tool to seed "realistic" data into the database (happens automatically in testing env), the tool running in background is:

```python -m app.utils.seed_db```

## Routes / Endpoints
| Route                        | Method   | Purpose                                                            |
| ---------------------------- | -------- | ------------------------------------------------------------------ |
| `/customers/<id>/events`     | **POST** | Record a new event (login, invoice, ticket, etc.) via JSON or form |
| `/customers/<id>/events/new` | **GET**  | Show HTML form for recording a new event                           |
| `/customers/<id>`            | **GET**  | Customer details + health score                                    |
| `/dashboard`                 | **GET**  | Dashboards: latest events, at-risk customers                       |


## Validation & Errors
* Forms: validated server-side, with flash() messages for feedback
* API (JSON): returns validation errors in JSON
* Handles:
 ** Missing required fields
 ** Invalid datetime formats
 ** Logical errors (e.g. closed_at < created_at)
 ** Numeric checks (invoice amounts must be positive)

 ## Testing
 Pytest is used for automated tests.

 ```pytest```

* Tests create temporary customers & events in a SQLite test DB
* Covers both JSON API and HTML form submissions
* Ensures validation & flash messages work