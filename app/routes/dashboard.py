from functools import wraps
from flask import Blueprint, current_app, g, make_response, request, jsonify
from ..models import ApiUsage, FeatureUsage, Invoice, LoginEvent, SupportTicket, Customer
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
def get_all_customers():
    if request.method == 'GET':
        with current_app.db_manager.get_read_session() as session:
            customers = session.query(Customer).all() 
            if not customers:
                return jsonify({'message': 'No customers in DB'}), 404
            return jsonify([c.to_dict() for c in customers]), 200
