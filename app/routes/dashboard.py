from functools import wraps
from flask import Blueprint, current_app, request, jsonify, render_template
from sqlalchemy import func
from app.routes.customer import calculate_customer_health
from ..models import ApiUsage, FeatureUsage, Invoice, LoginEvent, SupportTicket, Customer
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/dashboard")
def dashboard():
    with current_app.db_manager.get_read_session() as session:
        customers = session.query(Customer).all()

        customers_with_health = []
        for c in customers:
            score = calculate_customer_health(session, c.id).get("health_score", 0)
            customers_with_health.append({
                **c.to_dict(),
                "health_score": score
            })

        return render_template(
            "dashboard.html",
            total_customers=len(customers),
            avg_health=round(sum(c['health_score'] for c in customers_with_health) / len(customers_with_health), 2) if customers_with_health else 0,
            customers=customers_with_health
        )
