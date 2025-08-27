from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import Invoice, User, Transaction, InvoiceStatus, TransactionStatus, TransactionType
from database import db_manager
from user_helpers import UserManager
from transaction_helpers import TransactionManager
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import hashlib
import secrets

logger = logging.getLogger(__name__)

class InvoiceManager:
    """Helper functions for Lightning invoice management"""
    
    @staticmethod
    def create_invoice(phone_number: str, amount_sats: int, description: str = None,
                      expiry_minutes: int = 60) -> Optional[Invoice]:
        """
        Create a new Lightning invoice record.
        
        Args:
            phone_number: User's phone number
            amount_sats: Amount in satoshis
            description: Invoice description
            expiry_minutes: Invoice expiry time in minutes
            
        Returns:
            Invoice object if successful, None if failed
        """
        try:
            with db_manager.get_session() as session:
                # Get or create user
                user, _ = UserManager.create_or_get_user(phone_number)
                
                # Generate payment hash (in real implementation, this would come from Lightning node)
                payment_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
                
                # Generate Lightning invoice string (placeholder - replace with actual Lightning node call)
                invoice_string = f"lnbc{amount_sats}1pw{secrets.token_hex(20)}"
                
                # Calculate expiry time
                expires_at = datetime.now() + timedelta(minutes=expiry_minutes)
                
                # Create invoice record
                invoice = Invoice(
                    user_id=user.id,
                    invoice_string=invoice_string,
                    payment_hash=payment_hash,
                    amount_sats=amount_sats,
                    status=InvoiceStatus.PENDING.value,
                    description=description or f"Invoice for {amount_sats} sats",
                    expires_at=expires_at
                )
                
                session.add(invoice)
                session.commit()
                
                # Also log as a transaction
                TransactionManager.log_invoice_transaction(
                    phone_number, amount_sats, invoice_string, payment_hash, description
                )
                
                logger.info(f"Created invoice: {phone_number}, {amount_sats} sats, expires: {expires_at}")
                return invoice
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating invoice: {e}")
            return None
    
    @staticmethod
    def get_invoice_by_payment_hash(payment_hash: str) -> Optional[Invoice]:
        """
        Get invoice by payment hash.
        
        Args:
            payment_hash: Lightning payment hash
            
        Returns:
            Invoice object if found, None otherwise
        """
        try:
            with db_manager.get_session() as session:
                invoice = session.query(Invoice).filter_by(payment_hash=payment_hash).first()
                return invoice
        except SQLAlchemyError as e:
            logger.error(f"Error fetching invoice by payment hash: {e}")
            return None
    
    @staticmethod
    def get_invoice_by_string(invoice_string: str) -> Optional[Invoice]:
        """
        Get invoice by invoice string.
        
        Args:
            invoice_string: Lightning invoice string
            
        Returns:
            Invoice object if found, None otherwise
        """
        try:
            with db_manager.get_session() as session:
                invoice = session.query(Invoice).filter_by(invoice_string=invoice_string).first()
                return invoice
        except SQLAlchemyError as e:
            logger.error(f"Error fetching invoice by string: {e}")
            return None
    
    @staticmethod
    def mark_invoice_paid(payment_hash: str, paid_amount_sats: int = None) -> bool:
        """
        Mark invoice as paid and update user balance.
        
        Args:
            payment_hash: Lightning payment hash
            paid_amount_sats: Actual amount paid (should match invoice amount)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                # Get invoice with lock
                invoice = session.query(Invoice).filter_by(
                    payment_hash=payment_hash
                ).with_for_update().first()
                
                if not invoice:
                    logger.error(f"Invoice not found for payment hash: {payment_hash}")
                    return False
                
                if invoice.status != InvoiceStatus.PENDING.value:
                    logger.warning(f"Invoice already processed: {payment_hash}, status: {invoice.status}")
                    return False
                
                # Verify amount if provided
                if paid_amount_sats and paid_amount_sats != invoice.amount_sats:
                    logger.error(f"Payment amount mismatch: {paid_amount_sats} != {invoice.amount_sats}")
                    return False
                
                # Get user with lock for balance update
                user = session.query(User).filter_by(
                    id=invoice.user_id
                ).with_for_update().first()
                
                if not user:
                    logger.error(f"User not found for invoice: {invoice.user_id}")
                    return False
                
                # Update invoice status
                invoice.status = InvoiceStatus.PAID.value
                invoice.paid_at = datetime.now()
                
                # Add amount to user balance
                user.balance_sats += invoice.amount_sats
                
                # Update related transaction status
                transaction = session.query(Transaction).filter_by(
                    lightning_payment_hash=payment_hash,
                    transaction_type=TransactionType.INVOICE.value
                ).first()
                
                if transaction:
                    transaction.status = TransactionStatus.COMPLETED.value
                
                # Also log as a receive transaction
                receive_transaction = Transaction(
                    user_id=user.id,
                    transaction_type=TransactionType.RECEIVE.value,
                    amount_sats=invoice.amount_sats,
                    status=TransactionStatus.COMPLETED.value,
                    invoice_string=invoice.invoice_string,
                    lightning_payment_hash=payment_hash,
                    description=f"Invoice payment received: {invoice.description}"
                )
                session.add(receive_transaction)
                
                session.commit()
                
                logger.info(f"Invoice paid: {payment_hash}, {invoice.amount_sats} sats added to user {user.phone_number}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error marking invoice as paid: {e}")
            return False
    
    @staticmethod
    def expire_invoice(payment_hash: str) -> bool:
        """
        Mark invoice as expired.
        
        Args:
            payment_hash: Lightning payment hash
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                invoice = session.query(Invoice).filter_by(payment_hash=payment_hash).first()
                if not invoice:
                    logger.error(f"Invoice not found: {payment_hash}")
                    return False
                
                if invoice.status != InvoiceStatus.PENDING.value:
                    logger.warning(f"Cannot expire invoice with status: {invoice.status}")
                    return False
                
                invoice.status = InvoiceStatus.EXPIRED.value
                
                # Update related transaction status
                transaction = session.query(Transaction).filter_by(
                    lightning_payment_hash=payment_hash,
                    transaction_type=TransactionType.INVOICE.value
                ).first()
                
                if transaction:
                    transaction.status = TransactionStatus.EXPIRED.value
                
                session.commit()
                
                logger.info(f"Invoice expired: {payment_hash}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error expiring invoice: {e}")
            return False
    
    @staticmethod
    def cancel_invoice(payment_hash: str) -> bool:
        """
        Mark invoice as cancelled.
        
        Args:
            payment_hash: Lightning payment hash
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                invoice = session.query(Invoice).filter_by(payment_hash=payment_hash).first()
                if not invoice:
                    logger.error(f"Invoice not found: {payment_hash}")
                    return False
                
                if invoice.status != InvoiceStatus.PENDING.value:
                    logger.warning(f"Cannot cancel invoice with status: {invoice.status}")
                    return False
                
                invoice.status = InvoiceStatus.CANCELLED.value
                
                # Update related transaction status
                transaction = session.query(Transaction).filter_by(
                    lightning_payment_hash=payment_hash,
                    transaction_type=TransactionType.INVOICE.value
                ).first()
                
                if transaction:
                    transaction.status = TransactionStatus.FAILED.value
                
                session.commit()
                
                logger.info(f"Invoice cancelled: {payment_hash}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error cancelling invoice: {e}")
            return False
    
    @staticmethod
    def get_user_invoices(phone_number: str, status: str = None, limit: int = 20) -> List[Invoice]:
        """
        Get user's invoice history.
        
        Args:
            phone_number: User's phone number
            status: Filter by invoice status (optional)
            limit: Maximum number of invoices to return
            
        Returns:
            List of Invoice objects
        """
        try:
            with db_manager.get_session() as session:
                user = UserManager.get_user_by_phone(phone_number)
                if not user:
                    return []
                
                query = session.query(Invoice).filter_by(user_id=user.id)
                
                if status:
                    query = query.filter_by(status=status)
                
                invoices = query.order_by(Invoice.created_at.desc()).limit(limit).all()
                return invoices
                
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user invoices: {e}")
            return []
    
    @staticmethod
    def get_pending_invoices(phone_number: str = None) -> List[Invoice]:
        """
        Get pending invoices, optionally filtered by user.
        
        Args:
            phone_number: User's phone number (optional)
            
        Returns:
            List of pending Invoice objects
        """
        try:
            with db_manager.get_session() as session:
                query = session.query(Invoice).filter_by(status=InvoiceStatus.PENDING.value)
                
                if phone_number:
                    user = UserManager.get_user_by_phone(phone_number)
                    if user:
                        query = query.filter_by(user_id=user.id)
                    else:
                        return []
                
                invoices = query.order_by(Invoice.created_at.desc()).all()
                return invoices
                
        except SQLAlchemyError as e:
            logger.error(f"Error fetching pending invoices: {e}")
            return []
    
    @staticmethod
    def cleanup_expired_invoices() -> int:
        """
        Mark expired invoices and update their status.
        
        Returns:
            Number of invoices marked as expired
        """
        try:
            with db_manager.get_session() as session:
                current_time = datetime.now()
                
                # Find expired invoices that are still pending
                expired_invoices = session.query(Invoice).filter(
                    Invoice.status == InvoiceStatus.PENDING.value,
                    Invoice.expires_at < current_time
                )
                
                count = expired_invoices.count()
                
                # Update invoice status
                expired_invoices.update({
                    'status': InvoiceStatus.EXPIRED.value
                })
                
                # Update related transaction status
                expired_payment_hashes = [inv.payment_hash for inv in expired_invoices.all()]
                if expired_payment_hashes:
                    session.query(Transaction).filter(
                        Transaction.lightning_payment_hash.in_(expired_payment_hashes),
                        Transaction.transaction_type == TransactionType.INVOICE.value
                    ).update({
                        'status': TransactionStatus.EXPIRED.value
                    })
                
                session.commit()
                logger.info(f"Marked {count} invoices as expired")
                return count
                
        except SQLAlchemyError as e:
            logger.error(f"Error cleaning up expired invoices: {e}")
            return 0
    
    @staticmethod
    def get_invoice_stats(phone_number: str = None) -> dict:
        """
        Get invoice statistics.
        
        Args:
            phone_number: User's phone number (optional, for user-specific stats)
            
        Returns:
            Dictionary with invoice statistics
        """
        try:
            with db_manager.get_session() as session:
                query = session.query(Invoice)
                
                if phone_number:
                    user = UserManager.get_user_by_phone(phone_number)
                    if user:
                        query = query.filter_by(user_id=user.id)
                    else:
                        return {}
                
                total = query.count()
                pending = query.filter_by(status=InvoiceStatus.PENDING.value).count()
                paid = query.filter_by(status=InvoiceStatus.PAID.value).count()
                expired = query.filter_by(status=InvoiceStatus.EXPIRED.value).count()
                cancelled = query.filter_by(status=InvoiceStatus.CANCELLED.value).count()
                
                # Calculate total amounts
                paid_invoices = query.filter_by(status=InvoiceStatus.PAID.value).all()
                total_paid_amount = sum(inv.amount_sats for inv in paid_invoices)
                
                return {
                    'total_invoices': total,
                    'pending': pending,
                    'paid': paid,
                    'expired': expired,
                    'cancelled': cancelled,
                    'total_paid_amount_sats': total_paid_amount,
                    'success_rate': (paid / total * 100) if total > 0 else 0
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting invoice stats: {e}")
            return {}

# Convenience functions for USSD integration
def create_invoice_for_ussd(phone_number: str, amount_sats: int, 
                           description: str = None) -> Optional[Invoice]:
    """
    Create invoice for USSD flow.
    Wrapper function with USSD-specific logic.
    """
    return InvoiceManager.create_invoice(phone_number, amount_sats, description)

def send_invoice_with_logging(phone_number: str, amount_sats: int, 
                            description: str = None) -> Optional[str]:
    """
    Create and return invoice string for sending to user.
    This function integrates with your existing send_invoice operation.
    
    Returns:
        Invoice string if successful, None if failed
    """
    try:
        invoice = InvoiceManager.create_invoice(phone_number, amount_sats, description)
        if invoice:
            logger.info(f"Generated invoice for USSD: {phone_number}, {amount_sats} sats")
            return invoice.invoice_string
        return None
    except Exception as e:
        logger.error(f"Send invoice operation failed: {e}")
        return None

def check_invoice_payment(payment_hash: str) -> dict:
    """
    Check if an invoice has been paid.
    Used for polling invoice status in USSD flow.
    
    Returns:
        Dictionary with payment status info
    """
    try:
        invoice = InvoiceManager.get_invoice_by_payment_hash(payment_hash)
        if not invoice:
            return {'status': 'not_found'}
        
        return {
            'status': invoice.status,
            'amount_sats': invoice.amount_sats,
            'paid_at': invoice.paid_at.isoformat() if invoice.paid_at else None,
            'expires_at': invoice.expires_at.isoformat(),
            'is_expired': invoice.is_expired()
        }
    except Exception as e:
        logger.error(f"Error checking invoice payment: {e}")
        return {'status': 'error'}

if __name__ == "__main__":
    # Example usage and testing
    test_phone = "+254700123456"
    test_amount = 5000
    
    try:
        # Test invoice creation
        invoice = create_invoice_for_ussd(test_phone, test_amount, "Test invoice")
        print(f"Created invoice: {invoice}")
        
        if invoice:
            # Test invoice retrieval
            retrieved = InvoiceManager.get_invoice_by_payment_hash(invoice.payment_hash)
            print(f"Retrieved invoice: {retrieved}")
            
            # Test marking as paid
            paid = InvoiceManager.mark_invoice_paid(invoice.payment_hash)
            print(f"Marked as paid: {paid}")
            
            # Test payment status check
            status = check_invoice_payment(invoice.payment_hash)
            print(f"Payment status: {status}")
        
        # Test invoice stats
        stats = InvoiceManager.get_invoice_stats(test_phone)
        print(f"Invoice stats: {stats}")
        
        # Test cleanup
        cleaned = InvoiceManager.cleanup_expired_invoices()
        print(f"Cleaned {cleaned} expired invoices")
        
    except Exception as e:
        print(f"Test failed: {e}")