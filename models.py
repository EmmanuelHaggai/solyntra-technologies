from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from enum import Enum

Base = declarative_base()

class TransactionType(Enum):
    SEND = "send"
    RECEIVE = "receive" 
    INVOICE = "invoice"
    TOPUP = "topup"
    WITHDRAW = "withdraw"

class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

class InvoiceStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    lightning_pubkey = Column(String(66), nullable=True)  # 33 bytes hex = 66 chars
    balance_sats = Column(Integer, default=0, nullable=False)  # Balance in satoshis
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user", lazy="dynamic")
    ussd_sessions = relationship("UssdSession", back_populates="user", lazy="dynamic") 
    invoices = relationship("Invoice", back_populates="user", lazy="dynamic")
    
    def __repr__(self):
        return f"<User(phone={self.phone_number}, balance={self.balance_sats} sats)>"

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # send, receive, invoice, topup, withdraw
    amount_sats = Column(Integer, nullable=False)  # Amount in satoshis
    status = Column(String(20), default="pending", nullable=False)  # pending, completed, failed, expired
    invoice_string = Column(Text, nullable=True)  # Lightning invoice for relevant transactions
    mpesa_transaction_id = Column(String(50), nullable=True)  # For M-Pesa operations
    lightning_payment_hash = Column(String(64), nullable=True)  # Lightning payment hash
    recipient_phone = Column(String(20), nullable=True)  # For send operations
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_type_status', 'user_id', 'transaction_type', 'status'),
        Index('idx_created_at', 'created_at'),
        Index('idx_payment_hash', 'lightning_payment_hash'),
    )
    
    def __repr__(self):
        return f"<Transaction(type={self.transaction_type}, amount={self.amount_sats}, status={self.status})>"

class UssdSession(Base):
    __tablename__ = 'ussd_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    phone_number = Column(String(20), nullable=False)
    current_state = Column(String(50), default="main_menu", nullable=False)
    input_buffer = Column(Text, nullable=True)  # Store temporary user inputs as JSON
    last_activity = Column(DateTime, default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="ussd_sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_active', 'session_id', 'is_active'),
        Index('idx_phone_active', 'phone_number', 'is_active'),
        Index('idx_last_activity', 'last_activity'),
    )
    
    def is_expired(self, timeout_minutes=30):
        """Check if session has expired based on last activity"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)
    
    def __repr__(self):
        return f"<UssdSession(session_id={self.session_id}, state={self.current_state}, active={self.is_active})>"

class Invoice(Base):
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    invoice_string = Column(Text, unique=True, nullable=False)
    payment_hash = Column(String(64), unique=True, nullable=False, index=True)
    amount_sats = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, paid, expired, cancelled
    description = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="invoices")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_payment_hash', 'payment_hash'),
    )
    
    def is_expired(self):
        """Check if invoice has expired"""
        return datetime.now() > self.expires_at and self.status == "pending"
    
    def __repr__(self):
        return f"<Invoice(amount={self.amount_sats}, status={self.status}, expires_at={self.expires_at})>"