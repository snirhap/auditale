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
    segment = Column(String)

    logins = relationship("LoginEvent", back_populates="customer")
    features = relationship("FeatureUsage", back_populates="customer")
    tickets = relationship("SupportTicket", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    api_usage = relationship("ApiUsage", back_populates="customer")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "segment": self.segment
        }

class LoginEvent(db.Model):
    __tablename__ = "logins"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="logins")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "timestamp": self.timestamp.isoformat()
        }

class FeatureUsage(db.Model):
    __tablename__ = "feature_usage"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    feature_name = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", back_populates="features")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "feature_name": self.feature_name,
            "timestamp": self.timestamp.isoformat()
        }

class SupportTicket(db.Model):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    status = Column(String, default="open")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="tickets")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None
        }

class Invoice(db.Model):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="unpaid")

    customer = relationship("Customer", back_populates="invoices")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "issued_at": self.issued_at.isoformat(),
            "due_date": self.due_date.isoformat(),
            "paid_date": self.paid_date.isoformat() if self.paid_date else None,
            "amount": self.amount,
            "status": self.status
        }

class ApiUsage(db.Model):
    __tablename__ = "api_usage"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    api_endpoint = Column(String, nullable=False)

    customer = relationship("Customer", back_populates="api_usage")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "timestamp": self.timestamp.isoformat(),
            "api_endpoint": self.api_endpoint
        }