import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
import logging
from models import Base
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database manager for handling MySQL connections and sessions.
    Supports connection pooling and automatic session management.
    """
    
    def __init__(self, database_url=None):
        # Use configuration manager for database URL
        if database_url is None:
            database_url = Config.DATABASE_URL
        
        # Engine configuration for production use
        self.engine = create_engine(
            database_url,
            pool_size=20,          # Number of connections to keep in pool
            max_overflow=30,       # Additional connections when pool is full
            pool_timeout=30,       # Seconds to wait for connection
            pool_recycle=3600,     # Recycle connections after 1 hour
            pool_pre_ping=True,    # Verify connections before use
            echo=False             # Set to True for SQL debugging
        )
        
        # Session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Scoped session for thread safety
        self.ScopedSession = scoped_session(self.SessionLocal)
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables - USE WITH CAUTION"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("Database tables dropped")
        except SQLAlchemyError as e:
            logger.error(f"Error dropping tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.
        Automatically handles commit/rollback and session cleanup.
        
        Usage:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(phone_number=phone).first()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_scoped_session(self):
        """Get thread-safe scoped session"""
        return self.ScopedSession()
    
    def remove_scoped_session(self):
        """Remove scoped session"""
        self.ScopedSession.remove()
    
    def health_check(self):
        """Check database connectivity"""
        try:
            with self.get_session() as session:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

# Global database manager instance
# Initialize with your actual database URL
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
def get_session():
    """Get a new database session"""
    return db_manager.get_session()

def init_database():
    """Initialize database tables"""
    db_manager.create_tables()

def check_database_health():
    """Check if database is accessible"""
    return db_manager.health_check()

# Database configuration examples for different environments
DATABASE_CONFIGS = {
    'development': {
        'url': 'mysql+pymysql://dev_user:dev_pass@localhost:3306/ussd_lightning_dev',
        'pool_size': 5,
        'max_overflow': 10
    },
    'testing': {
        'url': 'mysql+pymysql://test_user:test_pass@localhost:3306/ussd_lightning_test',
        'pool_size': 3,
        'max_overflow': 5
    },
    'production': {
        'url': 'mysql+pymysql://prod_user:prod_pass@prod-host:3306/ussd_lightning_prod',
        'pool_size': 20,
        'max_overflow': 30,
        'pool_timeout': 30,
        'pool_recycle': 3600
    }
}

def create_database_manager(environment='development'):
    """Create database manager for specific environment"""
    config = DATABASE_CONFIGS.get(environment, DATABASE_CONFIGS['development'])
    url = config.pop('url')
    
    engine = create_engine(url, **config, pool_pre_ping=True, echo=False)
    
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.engine = engine
    manager.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    manager.ScopedSession = scoped_session(manager.SessionLocal)
    
    return manager

if __name__ == "__main__":
    # Example usage and testing
    print("Testing database connection...")
    
    try:
        # Initialize database
        init_database()
        print("✓ Database tables created successfully")
        
        # Test connection
        if check_database_health():
            print("✓ Database connection is healthy")
        else:
            print("✗ Database connection failed")
            
    except Exception as e:
        print(f"✗ Database setup failed: {e}")
        print("\nPlease ensure:")
        print("1. MySQL server is running")
        print("2. Database credentials are correct")
        print("3. Database exists or user has CREATE privileges")
        print("4. Required Python packages are installed: pip install sqlalchemy pymysql")