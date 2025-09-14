from functools import wraps
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, url_for
from app.routes.customer import calculate_customer_health
from ..models import ApiUsage, FeatureUsage, Invoice, LoginEvent, SupportTicket, Customer
from ..constants import Constants

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/dashboard")
def dashboard():
    with current_app.db_manager.get_read_session() as session:
        latest = latest_actions()
        risky = risky_customers()

        return render_template(
            "dashboard.html",
            latest_actions=latest,
            risky_customers=risky,
            health_score_risk_threshold=Constants.AtRiskThreshold
        )

@dashboard_bp.route("/dashboard/seed", methods=["POST"])
def seed_database():
    from utils.seed_db import seed
    seed(current_app)
    flash("Database seeded successfully.", "success")
    return redirect(url_for("dashboard.dashboard"))

def latest_actions():
    with current_app.db_manager.get_read_session() as session:
        latest_logins = session.query(LoginEvent).order_by(LoginEvent.timestamp.desc()).limit(5).all()
        latest_tickets = session.query(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(5).all()
        latest_invoices = session.query(Invoice).order_by(Invoice.issued_at.desc()).limit(5).all()
        latest_apis = session.query(ApiUsage).order_by(ApiUsage.timestamp.desc()).limit(5).all()
        latest_features = session.query(FeatureUsage).order_by(FeatureUsage.timestamp.desc()).limit(5).all()

        return {
            "logins": [l.to_dict() for l in latest_logins],
            "tickets": [t.to_dict() for t in latest_tickets],
            "invoices": [i.to_dict() for i in latest_invoices],
            "api_calls": [a.to_dict() for a in latest_apis],
            "feature_usages": [f.to_dict() for f in latest_features]
        }

def risky_customers():
    with current_app.db_manager.get_read_session() as session:
        customers = session.query(Customer).all()
        risky_customers_list = []
        
        for c in customers:
            health = calculate_customer_health(session, c.id)
            if health and health.get("health_score") <= Constants.AtRiskThreshold:
                risky_customers_list.append({
                    **c.to_dict(),
                    "health_score": health.get("health_score", 0),
                    "css_class": "table-danger"
                })

        return risky_customers_list