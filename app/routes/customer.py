from functools import wraps
from flask import Blueprint, current_app, make_response, request, jsonify, render_template
from sqlalchemy import func
from ..models import ApiUsage, FeatureUsage, Invoice, LoginEvent, SupportTicket, Customer
from datetime import datetime, timedelta, timezone

customer_bp = Blueprint('customers', __name__)

@customer_bp.route('/customers', methods=['GET'])
def get_all_customers():
    
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
            "customers_list.html",
            total_customers=len(customers),
            avg_health=round(sum(c['health_score'] for c in customers_with_health) / len(customers_with_health), 2) if customers_with_health else 0,
            customers=customers_with_health
        )


        # customers = session.query(Customer).all() 
        # if not customers:
        #     return jsonify({'message': 'No customers in DB'}), 404

        # response = []

        # for customer in customers:
        #     customer_health_score = calculate_customer_health(session, customer.id).get("health_score", 0)
        #     response.append({**customer.to_dict(), "health": customer_health_score})

        # return render_template("customers_list.html", customers=response, total_customers=len(customers),
        
@customer_bp.route('/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    with current_app.db_manager.get_read_session() as session:
        customer = session.query(Customer).filter_by(id=customer_id).first()
        if not customer:
            return render_template("customer.html", customer=None, health=None), 404

        customer_dict = customer.to_dict()
        
        # Calculate health
        health = calculate_customer_health(session, customer_id)
        customer_dict['health'] = health if health else None

        return render_template("customer.html", customer=customer_dict, health=health)

def calculate_customer_health(session, customer_id):
    customer = session.query(Customer).filter_by(id=customer_id).first()
    if not customer:
        return None
    
    now = datetime.now(timezone.utc)
    last_30d = now - timedelta(days=30)

    # Login frequency (last 30 days)
    login_count = session.query(func.count(LoginEvent.id)) \
                                .filter(LoginEvent.customer_id == customer_id,
                                        LoginEvent.timestamp >= last_30d).scalar() or 0
    login_score = min(login_count * 10, 100)  # 10 logins or more == maximum points

    # Feature adoption (unique features used / total features)
    total_features = session.query(func.count(func.distinct(FeatureUsage.feature_name))).scalar() or 0

    features_used = session.query(func.count(func.distinct(FeatureUsage.feature_name))) \
                                 .filter(FeatureUsage.customer_id == customer_id).scalar() or 0
    adoption_rate = features_used / total_features if total_features > 0 else 0
    adoption_score = min(int(adoption_rate * 100), 100)

    # Support tickets (penalty for open tickets)
    open_tickets = session.query(func.count(SupportTicket.id)) \
                                .filter(SupportTicket.customer_id == customer_id,
                                        SupportTicket.status == "open").scalar() or 0
    ticket_score = max(100 - (open_tickets * 20), 0)  # 5 open tickets or more == minimum points

    # Invoice payments (check paid and in time)
    customer_invoices = session.query(Invoice).filter(Invoice.customer_id==customer_id).all()
    if customer_invoices:
        unpaid_or_late_invoices = [
                invoice for invoice in customer_invoices if (invoice.status == 'unpaid' or (invoice.due_date and invoice.due_date > invoice.due_date))
            ]
        invoice_score = int(((len(customer_invoices) - len(unpaid_or_late_invoices)) / len(customer_invoices)) * 100)  # unpaid or late invoices or more reduce points
    else:
        invoice_score = 100

    # API usage trends (last 30 days)
    api_calls = session.query(func.count(ApiUsage.api_endpoint)) \
                                .filter(ApiUsage.customer_id == customer_id,
                                        ApiUsage.timestamp >= last_30d).scalar() or 0
    api_score = min(api_calls * 10, 100)  # 10+ calls == maximum points

    # Final weighted score
    # FIXME: Weights can be adjusted by configuration
    health_score = (
        login_score * 0.25 +
        adoption_score * 0.25 +
        ticket_score * 0.2 +
        invoice_score * 0.2 +
        api_score * 0.1
    )

    return {
        "customer_id": customer_id,
        "scores": {
            "logins": login_score,
            "feature_adoption": adoption_score,
            "support_tickets": ticket_score,
            "invoices": invoice_score,
            "api_usage": api_score,
        },
        "health_score": round(health_score, 2)
    }

@customer_bp.route('/customers/<int:customer_id>/health', methods=['GET'])
def get_customer_health(customer_id):
    if request.method == 'GET':
        with current_app.db_manager.get_read_session() as session:
            customer = session.query(Customer).filter_by(id=customer_id).first()
        
        if not customer:
            return render_template("customer.html", customer=None, health=None), 404

        customer_dict = customer.to_dict()
        
        # Calculate health
        health = calculate_customer_health(session, customer_id)
        customer_dict['health'] = health if health else None

        return render_template("customer_health.html", customer=customer_dict, health=health), 200

@customer_bp.route('/customers/<int:customer_id>/events', methods=['POST'])
def customer_events(customer_id):
    if request.method == 'POST':
        with current_app.db_manager.get_write_session() as session:
            customer = session.query(Customer).filter_by(id=customer_id).first()
            if not customer:
                return jsonify({'message': 'Customers not exist'}), 404
            
            payload = request.get_json()
            event_type = payload.get("event_type")
            data = payload.get("data", {})

            if not event_type:
                return jsonify({"error": "event_type is required"}), 400
            
            # Route event to the right model
            if event_type == "login":
                event = LoginEvent(customer_id=customer.id, 
                                   timestamp=data.get("timestamp", datetime.now(timezone.utc)))
            elif event_type == "feature":
                event = FeatureUsage(customer_id=customer.id,
                                     feature_name=data["feature_name"],
                                     timestamp=data.get("timestamp", datetime.now(timezone.utc)))
            elif event_type == "ticket":
                event = SupportTicket(customer_id=customer.id,
                                      status=data.get("status", "open"),
                                      created_at=data.get("created_at", datetime.now(timezone.utc)))
            elif event_type == "invoice":
                event = Invoice(customer_id=customer.id,
                                due_date=data["due_date"],
                                amount=data["amount"],
                                status=data.get("status", "unpaid"),
                                paid_date=data.get("paid_date"))
            elif event_type == "api":
                event = ApiUsage(customer_id=customer.id,
                                 call_count=data.get("call_count", 0),
                                 timestamp=data.get("timestamp", datetime.now(timezone.utc)))
            else:
                return jsonify({"error": f"Unknown event_type {event_type}"}), 400
            
            session.add(event)
            session.commit()

            return jsonify({"message": f"{event_type} event recorded", "event_id": event.id}), 201
    
    elif request.method == 'GET':
        # return all events for a customer
        pass