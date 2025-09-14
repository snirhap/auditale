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

### Docker Compose (With Write+Read DB Engines, nginex as Load balancer)
```
docker-compose up --build --scale web=3
```