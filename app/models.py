from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    segment = Column(String)  # e.g. Enterprise, SMB, Startup

    logins = relationship("LoginEvent", back_populates="customer")
    features = relationship("FeatureUsage", back_populates="customer")
    tickets = relationship("SupportTicket", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    api_usage = relationship("ApiUsage", back_populates="customer")

class LoginEvent(db.Model):
    __tablename__ = "logins"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="logins")

class FeatureUsage(db.Model):
    __tablename__ = "feature_usage"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    feature_name = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", back_populates="features")

class SupportTicket(db.Model):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    status = Column(String, default="open")  # open/closed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="tickets")

class Invoice(db.Model):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    due_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="unpaid")  # unpaid/paid/late

    customer = relationship("Customer", back_populates="invoices")

class ApiUsage(db.Model):
    __tablename__ = "api_usage"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    call_count = Column(Integer, default=0)

    customer = relationship("Customer", back_populates="api_usage")