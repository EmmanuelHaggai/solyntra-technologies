from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import UssdSession, User
from database import db_manager
from user_helpers import UserManager
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class UssdSessionManager:
    """Helper functions for USSD session management"""
    
    @staticmethod
    def create_or_update_session(session_id: str, phone_number: str, 
                                current_state: str = "main_menu", 
                                input_buffer: Dict[str, Any] = None) -> UssdSession:
        """
        Create a new USSD session or update existing one.
        
        Args:
            session_id: Unique USSD session identifier from Africastalking
            phone_number: User's phone number
            current_state: Current USSD menu state
            input_buffer: Dictionary to store temporary user inputs
            
        Returns:
            UssdSession object
        """
        try:
            with db_manager.get_session() as session:
                # Get or create user first
                user, _ = UserManager.create_or_get_user(phone_number)
                
                # Check if session already exists
                existing_session = session.query(UssdSession).filter_by(
                    session_id=session_id
                ).first()
                
                if existing_session:
                    # Update existing session
                    existing_session.current_state = current_state
                    existing_session.input_buffer = json.dumps(input_buffer or {})
                    existing_session.last_activity = datetime.now()
                    existing_session.is_active = True
                    
                    session.commit()
                    logger.info(f"Updated USSD session: {session_id}")
                    return existing_session
                
                # Create new session
                new_session = UssdSession(
                    session_id=session_id,
                    user_id=user.id,
                    phone_number=phone_number,
                    current_state=current_state,
                    input_buffer=json.dumps(input_buffer or {}),
                    is_active=True
                )
                
                session.add(new_session)
                session.commit()
                
                logger.info(f"Created new USSD session: {session_id}")
                return new_session
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating/updating USSD session {session_id}: {e}")
            raise
    
    @staticmethod
    def get_session(session_id: str) -> Optional[UssdSession]:
        """
        Get USSD session by session ID.
        
        Args:
            session_id: USSD session identifier
            
        Returns:
            UssdSession object if found, None otherwise
        """
        try:
            with db_manager.get_session() as session:
                ussd_session = session.query(UssdSession).filter_by(
                    session_id=session_id,
                    is_active=True
                ).first()
                return ussd_session
        except SQLAlchemyError as e:
            logger.error(f"Error fetching USSD session {session_id}: {e}")
            return None
    
    @staticmethod
    def update_session_state(session_id: str, new_state: str, 
                           input_buffer: Dict[str, Any] = None) -> bool:
        """
        Update USSD session state and input buffer.
        
        Args:
            session_id: USSD session identifier
            new_state: New USSD state
            input_buffer: Updated input buffer data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                ussd_session = session.query(UssdSession).filter_by(
                    session_id=session_id,
                    is_active=True
                ).first()
                
                if not ussd_session:
                    logger.error(f"Active USSD session not found: {session_id}")
                    return False
                
                ussd_session.current_state = new_state
                if input_buffer is not None:
                    ussd_session.input_buffer = json.dumps(input_buffer)
                ussd_session.last_activity = datetime.now()
                
                session.commit()
                logger.info(f"Updated USSD session state: {session_id} -> {new_state}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating USSD session state {session_id}: {e}")
            return False
    
    @staticmethod
    def add_to_input_buffer(session_id: str, key: str, value: Any) -> bool:
        """
        Add data to session input buffer.
        
        Args:
            session_id: USSD session identifier
            key: Buffer key
            value: Value to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                ussd_session = session.query(UssdSession).filter_by(
                    session_id=session_id,
                    is_active=True
                ).first()
                
                if not ussd_session:
                    logger.error(f"Active USSD session not found: {session_id}")
                    return False
                
                # Parse existing buffer or create new
                try:
                    buffer_data = json.loads(ussd_session.input_buffer or '{}')
                except json.JSONDecodeError:
                    buffer_data = {}
                
                buffer_data[key] = value
                ussd_session.input_buffer = json.dumps(buffer_data)
                ussd_session.last_activity = datetime.now()
                
                session.commit()
                logger.info(f"Added to USSD session buffer: {session_id}[{key}] = {value}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating USSD session buffer {session_id}: {e}")
            return False
    
    @staticmethod
    def get_input_buffer(session_id: str) -> Dict[str, Any]:
        """
        Get session input buffer data.
        
        Args:
            session_id: USSD session identifier
            
        Returns:
            Dictionary containing buffer data
        """
        try:
            ussd_session = UssdSessionManager.get_session(session_id)
            if not ussd_session:
                return {}
            
            try:
                return json.loads(ussd_session.input_buffer or '{}')
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in session buffer: {session_id}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting USSD session buffer {session_id}: {e}")
            return {}
    
    @staticmethod
    def end_session(session_id: str) -> bool:
        """
        Mark USSD session as inactive.
        
        Args:
            session_id: USSD session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                ussd_session = session.query(UssdSession).filter_by(
                    session_id=session_id
                ).first()
                
                if not ussd_session:
                    logger.warning(f"USSD session not found for ending: {session_id}")
                    return False
                
                ussd_session.is_active = False
                ussd_session.last_activity = datetime.now()
                
                session.commit()
                logger.info(f"Ended USSD session: {session_id}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error ending USSD session {session_id}: {e}")
            return False
    
    @staticmethod
    def cleanup_expired_sessions(timeout_minutes: int = 30) -> int:
        """
        Clean up expired USSD sessions.
        
        Args:
            timeout_minutes: Session timeout in minutes
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            with db_manager.get_session() as session:
                cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
                
                expired_sessions = session.query(UssdSession).filter(
                    UssdSession.is_active == True,
                    UssdSession.last_activity < cutoff_time
                )
                
                count = expired_sessions.count()
                expired_sessions.update({
                    'is_active': False,
                    'last_activity': datetime.now()
                })
                
                session.commit()
                logger.info(f"Cleaned up {count} expired USSD sessions")
                return count
                
        except SQLAlchemyError as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    @staticmethod
    def get_active_sessions_for_user(phone_number: str) -> list:
        """
        Get all active USSD sessions for a user.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            List of active UssdSession objects
        """
        try:
            with db_manager.get_session() as session:
                active_sessions = session.query(UssdSession).filter_by(
                    phone_number=phone_number,
                    is_active=True
                ).all()
                return active_sessions
        except SQLAlchemyError as e:
            logger.error(f"Error fetching active sessions for {phone_number}: {e}")
            return []
    
    @staticmethod
    def get_session_history(phone_number: str, limit: int = 10) -> list:
        """
        Get recent USSD session history for a user.
        
        Args:
            phone_number: User's phone number
            limit: Number of sessions to retrieve
            
        Returns:
            List of recent UssdSession objects
        """
        try:
            with db_manager.get_session() as session:
                sessions = session.query(UssdSession).filter_by(
                    phone_number=phone_number
                ).order_by(UssdSession.last_activity.desc()).limit(limit).all()
                return sessions
        except SQLAlchemyError as e:
            logger.error(f"Error fetching session history for {phone_number}: {e}")
            return []

# Convenience functions for backward compatibility
def create_or_update_session(session_id: str, phone_number: str, 
                           current_state: str = "main_menu", 
                           input_buffer: Dict[str, Any] = None) -> UssdSession:
    """Create or update USSD session - wrapper function"""
    return UssdSessionManager.create_or_update_session(session_id, phone_number, current_state, input_buffer)

def get_session(session_id: str) -> Optional[UssdSession]:
    """Get USSD session - wrapper function"""
    return UssdSessionManager.get_session(session_id)

def update_session_state(session_id: str, new_state: str, input_buffer: Dict[str, Any] = None) -> bool:
    """Update session state - wrapper function"""
    return UssdSessionManager.update_session_state(session_id, new_state, input_buffer)

def end_session(session_id: str) -> bool:
    """End USSD session - wrapper function"""
    return UssdSessionManager.end_session(session_id)

if __name__ == "__main__":
    # Example usage and testing
    test_session_id = "AT_SESSION_12345"
    test_phone = "+254700123456"
    
    try:
        # Test session creation
        session = create_or_update_session(test_session_id, test_phone, "main_menu")
        print(f"Created session: {session}")
        
        # Test adding to input buffer
        UssdSessionManager.add_to_input_buffer(test_session_id, "amount", "1000")
        UssdSessionManager.add_to_input_buffer(test_session_id, "recipient", "+254700987654")
        
        # Test getting buffer
        buffer = UssdSessionManager.get_input_buffer(test_session_id)
        print(f"Session buffer: {buffer}")
        
        # Test state update
        updated = update_session_state(test_session_id, "send_confirm")
        print(f"State updated: {updated}")
        
        # Test session cleanup
        cleaned = UssdSessionManager.cleanup_expired_sessions(0)  # Clean all for testing
        print(f"Cleaned {cleaned} sessions")
        
    except Exception as e:
        print(f"Test failed: {e}")