from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_
from models import Transaction, User, TransactionType, TransactionStatus
from database import db_manager
from user_helpers import UserManager
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal

logger = logging.getLogger(__name__)

class InsufficientBalanceError(Exception):
    """Raised when user has insufficient balance for a transaction"""
    pass

class TransactionManager:
    """Helper functions for transaction logging with atomic balance updates"""
    
    @staticmethod
    def log_send_transaction(sender_phone: str, recipient_phone: str, amount_sats: int,
                           lightning_payment_hash: str = None, invoice_string: str = None,
                           description: str = None) -> Optional[Transaction]:
        """
        Log a send transaction with atomic balance deduction.
        
        Args:
            sender_phone: Sender's phone number
            recipient_phone: Recipient's phone number  
            amount_sats: Amount in satoshis
            lightning_payment_hash: Lightning payment hash
            invoice_string: Lightning invoice if applicable
            description: Transaction description
            
        Returns:
            Transaction object if successful, None if failed
            
        Raises:
            InsufficientBalanceError: If sender has insufficient balance
        """
        try:
            with db_manager.get_session() as session:
                # Get sender user with row lock for atomic balance update
                sender = session.query(User).filter_by(
                    phone_number=sender_phone
                ).with_for_update().first()
                
                if not sender:
                    logger.error(f"Sender not found: {sender_phone}")
                    return None
                
                # Check sufficient balance
                if sender.balance_sats < amount_sats:
                    raise InsufficientBalanceError(
                        f"Insufficient balance: {sender.balance_sats} < {amount_sats} sats"
                    )
                
                # Deduct balance atomically
                sender.balance_sats -= amount_sats
                
                # Create transaction record
                transaction = Transaction(
                    user_id=sender.id,
                    transaction_type=TransactionType.SEND.value,
                    amount_sats=amount_sats,
                    status=TransactionStatus.PENDING.value,
                    invoice_string=invoice_string,
                    lightning_payment_hash=lightning_payment_hash,
                    recipient_phone=recipient_phone,
                    description=description or f"Send {amount_sats} sats to {recipient_phone}"
                )
                
                session.add(transaction)
                session.commit()
                
                logger.info(f"Logged send transaction: {sender_phone} -> {recipient_phone}, {amount_sats} sats")
                return transaction
                
        except InsufficientBalanceError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error logging send transaction: {e}")
            return None
    
    @staticmethod
    def log_receive_transaction(recipient_phone: str, amount_sats: int,
                              lightning_payment_hash: str = None, invoice_string: str = None,
                              description: str = None) -> Optional[Transaction]:
        """
        Log a receive transaction with atomic balance addition.
        
        Args:
            recipient_phone: Recipient's phone number
            amount_sats: Amount in satoshis
            lightning_payment_hash: Lightning payment hash
            invoice_string: Lightning invoice if applicable
            description: Transaction description
            
        Returns:
            Transaction object if successful, None if failed
        """
        try:
            with db_manager.get_session() as session:
                # Get or create recipient user
                recipient, _ = UserManager.create_or_get_user(recipient_phone)
                
                # Get user with row lock for atomic balance update
                recipient = session.query(User).filter_by(
                    phone_number=recipient_phone
                ).with_for_update().first()
                
                if not recipient:
                    logger.error(f"Recipient not found: {recipient_phone}")
                    return None
                
                # Add balance atomically
                recipient.balance_sats += amount_sats
                
                # Create transaction record
                transaction = Transaction(
                    user_id=recipient.id,
                    transaction_type=TransactionType.RECEIVE.value,
                    amount_sats=amount_sats,
                    status=TransactionStatus.COMPLETED.value,  # Receives are typically completed immediately
                    invoice_string=invoice_string,
                    lightning_payment_hash=lightning_payment_hash,
                    description=description or f"Received {amount_sats} sats"
                )
                
                session.add(transaction)
                session.commit()
                
                logger.info(f"Logged receive transaction: {recipient_phone}, {amount_sats} sats")
                return transaction
                
        except SQLAlchemyError as e:
            logger.error(f"Error logging receive transaction: {e}")
            return None
    
    @staticmethod
    def log_topup_transaction(phone_number: str, amount_sats: int,
                            mpesa_transaction_id: str, description: str = None) -> Optional[Transaction]:
        """
        Log M-Pesa topup transaction with atomic balance addition.
        
        Args:
            phone_number: User's phone number
            amount_sats: Amount in satoshis
            mpesa_transaction_id: M-Pesa transaction ID
            description: Transaction description
            
        Returns:
            Transaction object if successful, None if failed
        """
        try:
            with db_manager.get_session() as session:
                # Get or create user
                user, _ = UserManager.create_or_get_user(phone_number)
                
                # Get user with row lock for atomic balance update
                user = session.query(User).filter_by(
                    phone_number=phone_number
                ).with_for_update().first()
                
                if not user:
                    logger.error(f"User not found for topup: {phone_number}")
                    return None
                
                # Add balance atomically
                user.balance_sats += amount_sats
                
                # Create transaction record
                transaction = Transaction(
                    user_id=user.id,
                    transaction_type=TransactionType.TOPUP.value,
                    amount_sats=amount_sats,
                    status=TransactionStatus.COMPLETED.value,
                    mpesa_transaction_id=mpesa_transaction_id,
                    description=description or f"M-Pesa topup: {amount_sats} sats"
                )
                
                session.add(transaction)
                session.commit()
                
                logger.info(f"Logged topup transaction: {phone_number}, {amount_sats} sats, M-Pesa: {mpesa_transaction_id}")
                return transaction
                
        except SQLAlchemyError as e:
            logger.error(f"Error logging topup transaction: {e}")
            return None
    
    @staticmethod
    def log_withdraw_transaction(phone_number: str, amount_sats: int,
                               mpesa_transaction_id: str = None, description: str = None) -> Optional[Transaction]:
        """
        Log M-Pesa withdrawal transaction with atomic balance deduction.
        
        Args:
            phone_number: User's phone number
            amount_sats: Amount in satoshis
            mpesa_transaction_id: M-Pesa transaction ID (may be None if pending)
            description: Transaction description
            
        Returns:
            Transaction object if successful, None if failed
            
        Raises:
            InsufficientBalanceError: If user has insufficient balance
        """
        try:
            with db_manager.get_session() as session:
                # Get user with row lock for atomic balance update
                user = session.query(User).filter_by(
                    phone_number=phone_number
                ).with_for_update().first()
                
                if not user:
                    logger.error(f"User not found for withdrawal: {phone_number}")
                    return None
                
                # Check sufficient balance
                if user.balance_sats < amount_sats:
                    raise InsufficientBalanceError(
                        f"Insufficient balance for withdrawal: {user.balance_sats} < {amount_sats} sats"
                    )
                
                # Deduct balance atomically
                user.balance_sats -= amount_sats
                
                # Create transaction record
                transaction = Transaction(
                    user_id=user.id,
                    transaction_type=TransactionType.WITHDRAW.value,
                    amount_sats=amount_sats,
                    status=TransactionStatus.PENDING.value,  # Withdrawals start as pending
                    mpesa_transaction_id=mpesa_transaction_id,
                    description=description or f"M-Pesa withdrawal: {amount_sats} sats"
                )
                
                session.add(transaction)
                session.commit()
                
                logger.info(f"Logged withdrawal transaction: {phone_number}, {amount_sats} sats")
                return transaction
                
        except InsufficientBalanceError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error logging withdrawal transaction: {e}")
            return None
    
    @staticmethod
    def log_invoice_transaction(phone_number: str, amount_sats: int, invoice_string: str,
                              payment_hash: str, description: str = None) -> Optional[Transaction]:
        """
        Log Lightning invoice generation transaction.
        
        Args:
            phone_number: User's phone number
            amount_sats: Amount in satoshis
            invoice_string: Lightning invoice string
            payment_hash: Lightning payment hash
            description: Transaction description
            
        Returns:
            Transaction object if successful, None if failed
        """
        try:
            with db_manager.get_session() as session:
                # Get or create user
                user, _ = UserManager.create_or_get_user(phone_number)
                
                # Create transaction record
                transaction = Transaction(
                    user_id=user.id,
                    transaction_type=TransactionType.INVOICE.value,
                    amount_sats=amount_sats,
                    status=TransactionStatus.PENDING.value,
                    invoice_string=invoice_string,
                    lightning_payment_hash=payment_hash,
                    description=description or f"Generated invoice for {amount_sats} sats"
                )
                
                session.add(transaction)
                session.commit()
                
                logger.info(f"Logged invoice transaction: {phone_number}, {amount_sats} sats")
                return transaction
                
        except SQLAlchemyError as e:
            logger.error(f"Error logging invoice transaction: {e}")
            return None
    
    @staticmethod
    def update_transaction_status(transaction_id: int, new_status: str, 
                                mpesa_transaction_id: str = None) -> bool:
        """
        Update transaction status.
        
        Args:
            transaction_id: Transaction ID
            new_status: New transaction status
            mpesa_transaction_id: M-Pesa transaction ID if applicable
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                transaction = session.query(Transaction).filter_by(id=transaction_id).first()
                if not transaction:
                    logger.error(f"Transaction not found: {transaction_id}")
                    return False
                
                transaction.status = new_status
                if mpesa_transaction_id:
                    transaction.mpesa_transaction_id = mpesa_transaction_id
                
                session.commit()
                logger.info(f"Updated transaction {transaction_id} status to {new_status}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating transaction status: {e}")
            return False
    
    @staticmethod
    def get_user_transactions(phone_number: str, limit: int = 20, 
                            transaction_type: str = None) -> List[Transaction]:
        """
        Get user's transaction history.
        
        Args:
            phone_number: User's phone number
            limit: Maximum number of transactions to return
            transaction_type: Filter by transaction type (optional)
            
        Returns:
            List of Transaction objects
        """
        try:
            with db_manager.get_session() as session:
                user = UserManager.get_user_by_phone(phone_number)
                if not user:
                    return []
                
                query = session.query(Transaction).filter_by(user_id=user.id)
                
                if transaction_type:
                    query = query.filter_by(transaction_type=transaction_type)
                
                transactions = query.order_by(
                    Transaction.created_at.desc()
                ).limit(limit).all()
                
                return transactions
                
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user transactions: {e}")
            return []
    
    @staticmethod
    def get_pending_transactions(phone_number: str = None) -> List[Transaction]:
        """
        Get pending transactions, optionally filtered by user.
        
        Args:
            phone_number: User's phone number (optional)
            
        Returns:
            List of pending Transaction objects
        """
        try:
            with db_manager.get_session() as session:
                query = session.query(Transaction).filter_by(
                    status=TransactionStatus.PENDING.value
                )
                
                if phone_number:
                    user = UserManager.get_user_by_phone(phone_number)
                    if user:
                        query = query.filter_by(user_id=user.id)
                    else:
                        return []
                
                transactions = query.order_by(Transaction.created_at.desc()).all()
                return transactions
                
        except SQLAlchemyError as e:
            logger.error(f"Error fetching pending transactions: {e}")
            return []
    
    @staticmethod
    def reverse_failed_transaction(transaction_id: int, reason: str = "Transaction failed") -> bool:
        """
        Reverse a failed transaction by restoring user balance.
        Only works for send/withdraw transactions.
        
        Args:
            transaction_id: Transaction ID to reverse
            reason: Reason for reversal
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                transaction = session.query(Transaction).filter_by(id=transaction_id).first()
                if not transaction:
                    logger.error(f"Transaction not found for reversal: {transaction_id}")
                    return False
                
                # Only reverse send/withdraw transactions
                if transaction.transaction_type not in [TransactionType.SEND.value, TransactionType.WITHDRAW.value]:
                    logger.error(f"Cannot reverse transaction type: {transaction.transaction_type}")
                    return False
                
                # Get user with lock
                user = session.query(User).filter_by(
                    id=transaction.user_id
                ).with_for_update().first()
                
                if not user:
                    logger.error(f"User not found for transaction reversal: {transaction.user_id}")
                    return False
                
                # Restore balance
                user.balance_sats += transaction.amount_sats
                transaction.status = TransactionStatus.FAILED.value
                transaction.description += f" - REVERSED: {reason}"
                
                session.commit()
                logger.info(f"Reversed transaction {transaction_id}, restored {transaction.amount_sats} sats")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error reversing transaction: {e}")
            return False

# Wrapper functions for existing USSD operations
def send_btc_with_logging(sender_phone: str, recipient_phone: str, amount_sats: int,
                         lightning_payment_hash: str = None, invoice_string: str = None) -> Optional[Transaction]:
    """
    Wrapper for send_btc operation with database logging.
    Call this instead of direct send_btc to ensure transaction is logged.
    """
    try:
        # Log the transaction with atomic balance update
        transaction = TransactionManager.log_send_transaction(
            sender_phone, recipient_phone, amount_sats, 
            lightning_payment_hash, invoice_string
        )
        
        if transaction:
            # Here you would call your actual send_btc Lightning function
            # success = send_btc(recipient_phone, amount_sats, ...)
            # 
            # For now, we'll assume success and mark transaction as completed
            TransactionManager.update_transaction_status(transaction.id, TransactionStatus.COMPLETED.value)
            logger.info(f"Send BTC operation completed: {transaction.id}")
        
        return transaction
        
    except InsufficientBalanceError as e:
        logger.warning(f"Send BTC failed - insufficient balance: {e}")
        raise
    except Exception as e:
        logger.error(f"Send BTC operation failed: {e}")
        return None

def topup_mpesa_with_logging(phone_number: str, amount_sats: int, 
                           mpesa_transaction_id: str) -> Optional[Transaction]:
    """
    Wrapper for M-Pesa topup operation with database logging.
    Call this instead of direct topup to ensure transaction is logged.
    """
    try:
        return TransactionManager.log_topup_transaction(phone_number, amount_sats, mpesa_transaction_id)
    except Exception as e:
        logger.error(f"M-Pesa topup operation failed: {e}")
        return None

def withdraw_mpesa_with_logging(phone_number: str, amount_sats: int) -> Optional[Transaction]:
    """
    Wrapper for M-Pesa withdrawal operation with database logging.
    Call this instead of direct withdraw to ensure transaction is logged.
    """
    try:
        transaction = TransactionManager.log_withdraw_transaction(phone_number, amount_sats)
        
        if transaction:
            # Here you would call your actual withdraw_mpesa function
            # mpesa_id = withdraw_mpesa(phone_number, amount_sats, ...)
            # 
            # Update with M-Pesa transaction ID when available
            # TransactionManager.update_transaction_status(transaction.id, "completed", mpesa_id)
            pass
        
        return transaction
        
    except InsufficientBalanceError as e:
        logger.warning(f"M-Pesa withdrawal failed - insufficient balance: {e}")
        raise
    except Exception as e:
        logger.error(f"M-Pesa withdrawal operation failed: {e}")
        return None

if __name__ == "__main__":
    # Example usage and testing
    test_phone1 = "+254700123456"
    test_phone2 = "+254700987654"
    
    try:
        # Test topup
        topup_tx = topup_mpesa_with_logging(test_phone1, 10000, "MPesa123456")
        print(f"Topup transaction: {topup_tx}")
        
        # Test send with insufficient balance (should fail)
        try:
            send_tx = send_btc_with_logging(test_phone1, test_phone2, 20000)
            print(f"Send transaction: {send_tx}")
        except InsufficientBalanceError as e:
            print(f"Expected error: {e}")
        
        # Test send with sufficient balance
        send_tx = send_btc_with_logging(test_phone1, test_phone2, 5000)
        print(f"Send transaction: {send_tx}")
        
        # Get transaction history
        history = TransactionManager.get_user_transactions(test_phone1)
        print(f"Transaction history: {len(history)} transactions")
        
    except Exception as e:
        print(f"Test failed: {e}")