from functools import wraps
from flask import Blueprint, current_app, flash, make_response, redirect, request, jsonify, render_template, url_for
from sqlalchemy import desc, func
from app.constants import Constants
from ..models import ApiUsage, FeatureUsage, Invoice, LoginEvent, SupportTicket, Customer
from datetime import datetime, timedelta, timezone

customer_bp = Blueprint('customers', __name__)

@customer_bp.route('/customers', methods=['GET'])
def list_customers():
    sort_by = request.args.get("sort_by", "name")  # default sort
    order = request.args.get("order", "asc")
    
    # Prevent SQL injection by allowing only specific columns
    if sort_by not in ["name", "health_score"]:
        sort_by = "name"
    
    with current_app.db_manager.get_read_session() as session:
        customers = session.query(Customer).all()

        customers_with_health = []

        for c in customers:
            score = calculate_customer_health(session, c.id).get("health_score", 0)
            customers_with_health.append({
                **c.to_dict(),
                "health_score": score
            })
        
        # Sort in Python
        if sort_by == "health_score":
            customers_with_health.sort(key=lambda x: x["health_score"], reverse=(order=="desc"))
        else:  # default sort by name
            customers_with_health.sort(key=lambda x: x["name"].lower(), reverse=(order=="desc"))

        return render_template(
            "customers_list.html",
            total_customers=len(customers),
            avg_health=round(sum(c['health_score'] for c in customers_with_health) / len(customers_with_health), 2) if customers_with_health else 0,
            customers=customers_with_health
        )
        
@customer_bp.route('/customers/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    logins_page = request.args.get('logins_page', 1, type=int)
    invoice_page = request.args.get('invoice_page', 1, type=int)
    ticket_page = request.args.get('ticket_page', 1, type=int)
    api_page = request.args.get('api_page', 1, type=int)
    feature_page = request.args.get('feature_page', 1, type=int)
    per_page = 5  # items per page

    with current_app.db_manager.get_read_session() as session:
        customer = session.query(Customer).filter_by(id=customer_id).first()
        if not customer:
            return render_template("customer.html", customer=None, health=None), 404
        
        # Paginate logins
        logins = (
            session.query(LoginEvent)
            .filter_by(customer_id=customer_id)
            .order_by(LoginEvent.timestamp.desc())
            .offset((api_page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        total_logins = session.query(LoginEvent).filter_by(customer_id=customer_id).count()

        # Paginate invoices
        invoices = (
            session.query(Invoice)
            .filter_by(customer_id=customer_id)
            .order_by(Invoice.issued_at.desc())
            .offset((invoice_page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        print(f'Fetched {len(invoices)} invoices for customer {customer_id}')  # Debugging line
        total_invoices = session.query(Invoice).filter_by(customer_id=customer_id).count()
        
        # Paginate tickets
        tickets = (
            session.query(SupportTicket)
            .filter_by(customer_id=customer_id)
            .order_by(SupportTicket.created_at.desc())
            .offset((ticket_page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        total_tickets = session.query(SupportTicket).filter_by(customer_id=customer_id).count()

        # Paginate API calls
        apis = (
            session.query(ApiUsage)
            .filter_by(customer_id=customer_id)
            .order_by(ApiUsage.timestamp.desc())
            .offset((api_page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        total_apis = session.query(ApiUsage).filter_by(customer_id=customer_id).count()
        
        # Paginate feature usages
        features = (
            session.query(FeatureUsage)
            .filter_by(customer_id=customer_id)
            .order_by(FeatureUsage.timestamp.desc())
            .offset((api_page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        total_features = session.query(FeatureUsage).filter_by(customer_id=customer_id).count()

        # Calculate health
        health_details = calculate_customer_health(session, customer_id)

        return render_template("customer.html", 
                               customer=customer,
                               logins=logins,
                               invoices=invoices,
                               tickets=tickets,
                               apis=apis,
                               features=features,
                               logins_page=logins_page,
                               invoice_page=invoice_page,
                               ticket_page=ticket_page,
                               api_page=api_page,
                               feature_page=feature_page,
                               per_page=per_page,
                               total_logins=total_logins,
                               total_invoices=total_invoices,
                               total_tickets=total_tickets,
                               total_apis=total_apis,
                               total_features=total_features,
                               health=health_details), 200

def calculate_customer_health(session, customer_id):
    customer = session.query(Customer).filter_by(id=customer_id).first()
    if not customer:
        return None
    
    now = datetime.now()
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
    health_score = (
        login_score * Constants.LOGIN_WEIGHT +
        adoption_score * Constants.FEATURE_ADOPTION_WEIGHT +
        ticket_score * Constants.SUPPORT_TICKET_WEIGHT +
        invoice_score * Constants.INVOICE_WEIGHT +
        api_score * Constants.API_USAGE_WEIGHT
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

def parse_iso_datetime(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"{date_str} is not a valid ISO 8601 datetime string")

@customer_bp.route("/customers/<int:customer_id>/events/new", methods=['GET'])
def new_customer_event(customer_id):
    with current_app.db_manager.get_read_session() as session:
        customer = session.query(Customer).filter_by(id=customer_id).first()
        if not customer:
            return jsonify({"message": "Customer does not exist"}), 404
        return render_template("new_customer_event.html", customer=customer)

@customer_bp.route('/customers/<int:customer_id>/events', methods=['POST'])
def record_customer_event(customer_id):
    with current_app.db_manager.get_write_session() as session:
        customer = session.query(Customer).filter_by(id=customer_id).first()
        if not customer:
            flash("Customer does not exist.", "danger")
            return redirect(url_for("dashboard.dashboard"))
        
        if request.is_json:
            payload = request.get_json()
        else:
            # Convert form data into dict (like JSON shape you expect)
            payload = request.form.to_dict()
        
        event_type = payload.get("event_type")

        if not event_type:
            flash("Event type is required.", "danger")
            return redirect(url_for("customers.new_customer_event", customer_id=customer_id))

        try:
            # Login Event
            if event_type == "login":
                ts = payload.get("timestamp")
                if not ts:
                    flash("Timestamp is required for login event.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                
                timestamp = parse_iso_datetime(ts)
                if timestamp > datetime.now():
                    flash("Timestamp cannot be in the future.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                event = LoginEvent(customer_id=customer.id, timestamp=timestamp)
            
            # Feature Usage Event
            elif event_type == "feature":
                fname = payload.get("feature_name")
                ts = payload.get("timestamp")
                if not fname or not ts:
                    flash("Feature name and timestamp are required for feature event.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                
                timestamp = parse_iso_datetime(ts)

                if timestamp > datetime.now():
                    flash("Timestamp cannot be in the future.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                
                event = FeatureUsage(customer_id=customer.id, feature_name=fname, timestamp=timestamp)
            
            # Support Ticket Event
            elif event_type == "ticket":
                created_at = payload.get("created_at")
                closed_at = payload.get("closed_at")
                if not created_at:
                    flash("created_at is required for ticket event.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))

                created_dt = parse_iso_datetime(created_at)
                closed_dt = parse_iso_datetime(closed_at) if closed_at else None
                
                if closed_dt and closed_dt < created_dt:
                    flash("closed_at cannot be before created_at.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))

                if created_dt > datetime.now() or (closed_dt and closed_dt > datetime.now()):
                    flash("created_at or closed_at cannot be in the future.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))

                event = SupportTicket(
                    customer_id=customer.id,
                    status=payload.get("status", "open"),
                    created_at=created_dt,
                    closed_at=closed_dt
                )

            # Invoice Event
            elif event_type == "invoice":
                required_fields = ["issued_at", "due_date", "amount"]
                missing = [f for f in required_fields if f not in payload or payload[f] in [None, ""]]
                
                if missing:
                    flash(f"Missing required fields for invoice event: {', '.join(missing)}", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                
                issued_at = parse_iso_datetime(payload.get("issued_at"))
                due_date = parse_iso_datetime(payload.get("due_date"))

                if issued_at > datetime.now():
                    flash("issued_at cannot be in the future.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                
                if payload["due_date"] < payload["issued_at"]:
                    flash("due_date cannot be before issued_at.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))

                try:
                    amount = float(payload["amount"])
                    if amount < 0:
                        flash("Amount must be positive", "danger")
                        return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                except ValueError:
                    flash("Amount must be a valid number.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))

                event = Invoice(
                    customer_id=customer.id,
                    issued_at=issued_at,
                    due_date=due_date,
                    amount=amount,
                    status=payload.get("status", "unpaid"),
                    paid_date=parse_iso_datetime(payload.get("paid_date"))
                )
            
            # API Usage Event
            elif event_type == "api":
                print('API Usage Event')
                endpoint = payload.get("endpoint")
                ts = payload.get("timestamp")
                if not endpoint or not ts:
                    flash("Endpoint and timestamp are required for API event.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                
                if ts > datetime.now().isoformat():
                    flash("Timestamp cannot be in the future.", "danger")
                    return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
                
                timestamp = parse_iso_datetime(ts)
                event = ApiUsage(customer_id=customer.id, api_endpoint=endpoint, timestamp=timestamp)
            else:
                flash(f"Unknown event type: {event_type}", "danger")
                return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
            
            session.add(event)
            session.commit()
            flash(f"{event_type.capitalize()} event recorded successfully.", "success")
            return redirect(url_for("customers.get_customer", customer_id=customer_id))
        except KeyError as e:
            flash(f"Missing required field: {str(e)}", "danger")
            return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
        except ValueError as e:
            flash(f"Invalid data format: {str(e)}", "danger")
            return redirect(url_for("customers.new_customer_event", customer_id=customer_id))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for("customers.new_customer_event", customer_id=customer_id))