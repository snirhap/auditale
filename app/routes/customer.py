from functools import wraps
from flask import Blueprint, current_app, g, make_response, request, jsonify
from app.routes.auth import jwt_required
from ..models import ApiUsage, FeatureUsage, Invoice, LoginEvent, SupportTicket, Customer
from datetime import datetime

customer_bp = Blueprint('customers', __name__)

@customer_bp.route('/customers', methods=['GET'])
def get_all_customers():
    if request.method == 'GET':
        with current_app.db_manager.get_read_session() as session:
            customers = session.query(Customer).all() 
            if not customers:
                return jsonify({'message': 'No customers in DB'}), 404
            return jsonify([c.to_dict() for c in customers]), 200
        
@customer_bp.route('/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    if request.method == 'GET':
        with current_app.db_manager.get_read_session() as session:
            customer = session.query(Customer).filter_by(id=customer_id).first()
            if not customer:
                return jsonify({'message': 'Customers not exist'}), 404
            return jsonify(customer.to_dict()), 200

@customer_bp.route('/customers/<int:customer_id>/health', methods=['GET'])
def get_customer(customer_id):
    if request.method == 'GET':
        with current_app.db_manager.get_read_session() as session:
            customer = session.query(Customer).filter_by(id=customer_id).first()
            if not customer:
                return jsonify({'message': 'Customers not exist'}), 404
            
            # Calculate health score and return
            # ....

            return jsonify(customer.to_dict()), 200
        

@customer_bp.route('/customers/<int:customer_id>/events', methods=['POST'])
def record_event(customer_id):
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
                                   timestamp=data.get("timestamp", datetime.utcnow()))
            elif event_type == "feature":
                event = FeatureUsage(customer_id=customer.id,
                                     feature_name=data["feature_name"],
                                     timestamp=data.get("timestamp", datetime.utcnow()))
            elif event_type == "ticket":
                event = SupportTicket(customer_id=customer.id,
                                      status=data.get("status", "open"),
                                      created_at=data.get("created_at", datetime.utcnow()))
            elif event_type == "invoice":
                event = Invoice(customer_id=customer.id,
                                due_date=data["due_date"],
                                amount=data["amount"],
                                status=data.get("status", "unpaid"),
                                paid_date=data.get("paid_date"))
            elif event_type == "api":
                event = ApiUsage(customer_id=customer.id,
                                 call_count=data.get("call_count", 0),
                                 timestamp=data.get("timestamp", datetime.utcnow()))
            else:
                return jsonify({"error": f"Unknown event_type {event_type}"}), 400
            
            session.add(event)
            session.commit()

            return jsonify({"message": f"{event_type} event recorded", "event_id": event.id}), 201

    
    elif request.method == 'GET':
        # return all events for a customer
        pass