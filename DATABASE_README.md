# USSD Bitcoin Lightning Network - MySQL Integration

A complete MySQL database integration for your Africastalking USSD Bitcoin Lightning Network application using SQLAlchemy ORM.

## Features

- **SQLAlchemy Models**: User, Transaction, UssdSession, and Invoice models with proper relationships and indexes
- **Atomic Balance Updates**: Thread-safe balance operations with row locking
- **Transaction Logging**: Automatic logging for all Bitcoin and M-Pesa operations
- **Session Management**: USSD session state tracking with automatic cleanup
- **Invoice Management**: Lightning invoice creation, tracking, and status updates
- **Error Handling**: Comprehensive error handling with insufficient balance protection
- **Production Ready**: Connection pooling, proper logging, and database health checks

## Database Schema

### User Table
- `id`: Primary key
- `phone_number`: Unique phone number (indexed)
- `lightning_pubkey`: Lightning Network public key
- `balance_sats`: Balance in satoshis
- `created_at`, `updated_at`: Timestamps

### Transaction Table  
- `id`: Primary key
- `user_id`: Foreign key to User
- `transaction_type`: send, receive, invoice, topup, withdraw
- `amount_sats`: Amount in satoshis
- `status`: pending, completed, failed, expired
- `invoice_string`: Lightning invoice (if applicable)
- `lightning_payment_hash`: Lightning payment hash
- `mpesa_transaction_id`: M-Pesa transaction ID
- `recipient_phone`: For send operations
- `description`: Transaction description
- `created_at`, `updated_at`: Timestamps

### UssdSession Table
- `id`: Primary key  
- `session_id`: Africastalking session ID (unique, indexed)
- `user_id`: Foreign key to User
- `phone_number`: User's phone number
- `current_state`: Current USSD menu state
- `input_buffer`: JSON buffer for temporary data
- `last_activity`: Last activity timestamp
- `is_active`: Active session flag
- `created_at`: Timestamp

### Invoice Table
- `id`: Primary key
- `user_id`: Foreign key to User
- `invoice_string`: Lightning invoice string (unique)
- `payment_hash`: Lightning payment hash (unique, indexed)
- `amount_sats`: Invoice amount
- `status`: pending, paid, expired, cancelled
- `description`: Invoice description
- `expires_at`: Expiration timestamp
- `paid_at`: Payment timestamp
- `created_at`, `updated_at`: Timestamps

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Configure database connection in `database.py`:
```python
DATABASE_URL = 'mysql+pymysql://username:password@localhost:3306/ussd_lightning_db'
```

3. Initialize database:
```python
from database import init_database
init_database()
```

## Usage Examples

### User Management
```python
from user_helpers import UserManager

# Create or get user
user, created = UserManager.create_or_get_user("+254700123456", lightning_pubkey)

# Check balance
balance = UserManager.get_user_balance("+254700123456")

# Check if user exists  
exists = UserManager.user_exists("+254700123456")
```

### Transaction Logging
```python
from transaction_helpers import TransactionManager, send_btc_with_logging

# Log send transaction with atomic balance deduction
try:
    transaction = send_btc_with_logging(
        sender_phone="+254700123456",
        recipient_phone="+254700987654", 
        amount_sats=5000
    )
except InsufficientBalanceError:
    print("Insufficient balance")

# Log M-Pesa topup with balance addition
transaction = TransactionManager.log_topup_transaction(
    phone_number="+254700123456",
    amount_sats=10000,
    mpesa_transaction_id="MPesa123456"
)

# Get transaction history
history = TransactionManager.get_user_transactions("+254700123456", limit=10)
```

### USSD Session Management
```python
from session_helpers import UssdSessionManager

# Create/update session
session = UssdSessionManager.create_or_update_session(
    session_id="AT_SESSION_123",
    phone_number="+254700123456", 
    current_state="main_menu"
)

# Add data to input buffer
UssdSessionManager.add_to_input_buffer("AT_SESSION_123", "amount", 1000)

# Update session state
UssdSessionManager.update_session_state("AT_SESSION_123", "send_confirm")

# End session
UssdSessionManager.end_session("AT_SESSION_123")
```

### Invoice Management
```python
from invoice_helpers import InvoiceManager, send_invoice_with_logging

# Create invoice
invoice = InvoiceManager.create_invoice(
    phone_number="+254700123456",
    amount_sats=5000,
    description="Payment for services"
)

# Generate invoice for USSD
invoice_string = send_invoice_with_logging("+254700123456", 5000)

# Mark invoice as paid
InvoiceManager.mark_invoice_paid(payment_hash)

# Check payment status
status = check_invoice_payment(payment_hash)
```

## USSD Integration

The `ussd_integration_example.py` shows how to integrate with your existing USSD handler:

```python
from ussd_integration_example import UssdHandler

handler = UssdHandler()
response = handler.handle_ussd_request(session_id, phone_number, text)
```

## Integration with Existing Operations

Replace your existing function calls with database-integrated versions:

### Before (without database)
```python
# Your existing functions
send_btc(recipient_phone, amount_sats)
topup_mpesa(phone_number, amount_kes) 
withdraw_mpesa(phone_number, amount_sats)
send_invoice(phone_number, amount_sats)
```

### After (with database integration)
```python
# Database-integrated versions
send_btc_with_logging(sender_phone, recipient_phone, amount_sats)
topup_mpesa_with_logging(phone_number, amount_sats, mpesa_tx_id)
withdraw_mpesa_with_logging(phone_number, amount_sats) 
send_invoice_with_logging(phone_number, amount_sats)
```

## Maintenance Tasks

Set up periodic cleanup tasks:

```python
from ussd_integration_example import cleanup_expired_data

# Run this periodically (e.g., hourly cron job)
cleanup_expired_data()
```

## Database Migration to PostgreSQL

To migrate to PostgreSQL later, simply change the DATABASE_URL:

```python
# PostgreSQL
DATABASE_URL = 'postgresql+psycopg2://username:password@localhost:5432/ussd_lightning_db'
```

All SQLAlchemy models and operations remain the same.

## Production Deployment

1. **Database Security**: Use environment variables for database credentials
2. **Connection Pooling**: Configured automatically with recommended settings
3. **Logging**: Structured logging for monitoring and debugging
4. **Error Handling**: Comprehensive error handling with transaction rollback
5. **Indexes**: Proper database indexes for performance
6. **Health Checks**: Database connectivity monitoring

## File Structure

```
my_project/
├── models.py                     # SQLAlchemy models
├── database.py                   # Database connection and setup
├── user_helpers.py               # User management operations
├── session_helpers.py            # USSD session management
├── transaction_helpers.py        # Transaction logging with atomic updates
├── invoice_helpers.py            # Lightning invoice management
├── ussd_integration_example.py   # Complete USSD handler example
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Next Steps

1. Update `database.py` with your actual MySQL credentials
2. Replace placeholder Lightning operations with your actual implementations
3. Configure Africastalking webhook to point to your `/ussd` endpoint
4. Set up periodic maintenance tasks
5. Add monitoring and alerting for production use

The database layer is now ready to seamlessly integrate with your existing USSD Bitcoin Lightning Network application while providing robust data persistence and transaction safety.