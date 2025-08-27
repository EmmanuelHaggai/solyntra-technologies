from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from models import User
from database import db_manager
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class UserManager:
    """Helper functions for user management operations"""
    
    @staticmethod
    def create_or_get_user(phone_number: str, lightning_pubkey: str = None) -> Tuple[User, bool]:
        """
        Create a new user or fetch existing user by phone number.
        
        Args:
            phone_number: User's phone number (primary identifier)
            lightning_pubkey: Optional Lightning Network public key
            
        Returns:
            Tuple of (User object, created_flag)
            created_flag is True if user was newly created, False if existing
        """
        try:
            with db_manager.get_session() as session:
                # Check if user already exists
                existing_user = session.query(User).filter_by(phone_number=phone_number).first()
                
                if existing_user:
                    logger.info(f"Found existing user: {phone_number}")
                    # Update pubkey if provided and different
                    if lightning_pubkey and existing_user.lightning_pubkey != lightning_pubkey:
                        existing_user.lightning_pubkey = lightning_pubkey
                        session.commit()
                        logger.info(f"Updated Lightning pubkey for user: {phone_number}")
                    
                    return existing_user, False
                
                # Create new user
                new_user = User(
                    phone_number=phone_number,
                    lightning_pubkey=lightning_pubkey,
                    balance_sats=0
                )
                
                session.add(new_user)
                session.commit()
                
                logger.info(f"Created new user: {phone_number}")
                return new_user, True
                
        except IntegrityError as e:
            logger.error(f"Integrity error creating user {phone_number}: {e}")
            # Handle race condition - user might have been created by another process
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(phone_number=phone_number).first()
                if user:
                    return user, False
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error in create_or_get_user: {e}")
            raise
    
    @staticmethod
    def get_user_by_phone(phone_number: str) -> Optional[User]:
        """
        Get user by phone number.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            User object if found, None otherwise
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(phone_number=phone_number).first()
                return user
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user {phone_number}: {e}")
            raise
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User's database ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                return user
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user by ID {user_id}: {e}")
            raise
    
    @staticmethod
    def update_user_balance(phone_number: str, new_balance: int) -> bool:
        """
        Update user's balance (use with caution - prefer atomic operations).
        
        Args:
            phone_number: User's phone number
            new_balance: New balance in satoshis
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(phone_number=phone_number).first()
                if not user:
                    logger.error(f"User not found for balance update: {phone_number}")
                    return False
                
                old_balance = user.balance_sats
                user.balance_sats = new_balance
                session.commit()
                
                logger.info(f"Updated balance for {phone_number}: {old_balance} -> {new_balance} sats")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating balance for {phone_number}: {e}")
            return False
    
    @staticmethod
    def update_lightning_pubkey(phone_number: str, lightning_pubkey: str) -> bool:
        """
        Update user's Lightning Network public key.
        
        Args:
            phone_number: User's phone number
            lightning_pubkey: Lightning Network public key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(phone_number=phone_number).first()
                if not user:
                    logger.error(f"User not found for pubkey update: {phone_number}")
                    return False
                
                user.lightning_pubkey = lightning_pubkey
                session.commit()
                
                logger.info(f"Updated Lightning pubkey for {phone_number}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating Lightning pubkey for {phone_number}: {e}")
            return False
    
    @staticmethod
    def get_user_balance(phone_number: str) -> Optional[int]:
        """
        Get user's current balance.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Balance in satoshis if user exists, None otherwise
        """
        try:
            user = UserManager.get_user_by_phone(phone_number)
            return user.balance_sats if user else None
        except Exception as e:
            logger.error(f"Error getting balance for {phone_number}: {e}")
            return None
    
    @staticmethod
    def user_exists(phone_number: str) -> bool:
        """
        Check if user exists.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            user = UserManager.get_user_by_phone(phone_number)
            return user is not None
        except Exception as e:
            logger.error(f"Error checking if user exists {phone_number}: {e}")
            return False
    
    @staticmethod
    def get_all_users_with_balance() -> list:
        """
        Get all users who have a positive balance.
        Useful for administrative tasks.
        
        Returns:
            List of User objects with positive balance
        """
        try:
            with db_manager.get_session() as session:
                users = session.query(User).filter(User.balance_sats > 0).all()
                return users
        except SQLAlchemyError as e:
            logger.error(f"Error fetching users with balance: {e}")
            return []

# Convenience functions for backward compatibility
def create_or_get_user(phone_number: str, lightning_pubkey: str = None) -> Tuple[User, bool]:
    """Create or get user - wrapper function"""
    return UserManager.create_or_get_user(phone_number, lightning_pubkey)

def get_user_by_phone(phone_number: str) -> Optional[User]:
    """Get user by phone - wrapper function"""
    return UserManager.get_user_by_phone(phone_number)

def get_user_balance(phone_number: str) -> Optional[int]:
    """Get user balance - wrapper function"""
    return UserManager.get_user_balance(phone_number)

def user_exists(phone_number: str) -> bool:
    """Check if user exists - wrapper function"""
    return UserManager.user_exists(phone_number)

if __name__ == "__main__":
    # Example usage and testing
    test_phone = "+254700123456"
    test_pubkey = "03a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890"
    
    try:
        # Test user creation
        user, created = create_or_get_user(test_phone, test_pubkey)
        print(f"User {'created' if created else 'retrieved'}: {user}")
        
        # Test balance retrieval
        balance = get_user_balance(test_phone)
        print(f"User balance: {balance} sats")
        
        # Test user existence check
        exists = user_exists(test_phone)
        print(f"User exists: {exists}")
        
    except Exception as e:
        print(f"Test failed: {e}")