"""
Configuration management for USSD Bitcoin Lightning Network application
Loads environment variables and provides centralized config access
"""
import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    """Application configuration class"""
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://username:password@localhost:3306/ussd_lightning_db')
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Africastalking Configuration
    AFRICASTALKING_USERNAME = os.getenv('AFRICASTALKING_USERNAME')
    AFRICASTALKING_API_KEY = os.getenv('AFRICASTALKING_API_KEY')
    AFRICASTALKING_USSD_CODE = os.getenv('AFRICASTALKING_USSD_CODE', '*384*96#')
    
    # Lightning Network Configuration
    LIGHTNING_API_TYPE = os.getenv('LIGHTNING_API_TYPE', 'mock')
    
    # LNbits Configuration
    LNBITS_URL = os.getenv('LNBITS_URL')
    LNBITS_ADMIN_KEY = os.getenv('LNBITS_ADMIN_KEY')
    LNBITS_WALLET_KEY = os.getenv('LNBITS_WALLET_KEY')
    
    # LND Configuration  
    LND_URL = os.getenv('LND_URL', 'https://localhost:8080')
    LND_MACAROON = os.getenv('LND_MACAROON')
    LND_SKIP_VERIFY = os.getenv('LND_SKIP_VERIFY', 'false').lower() == 'true'
    
    # BTCPay Server Configuration
    BTCPAY_URL = os.getenv('BTCPAY_URL')
    BTCPAY_API_KEY = os.getenv('BTCPAY_API_KEY')
    BTCPAY_STORE_ID = os.getenv('BTCPAY_STORE_ID')
    
    # M-Pesa Configuration
    MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
    MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
    MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
    MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
    
    # Flask Configuration
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate_required_keys(cls):
        """Validate that required API keys are present"""
        required_keys = {
            'DATABASE_URL': cls.DATABASE_URL,
            'OPENAI_API_KEY': cls.OPENAI_API_KEY,
        }
        
        missing_keys = []
        for key, value in required_keys.items():
            if not value or value == 'your_api_key_here':
                missing_keys.append(key)
        
        if missing_keys:
            logger.warning(f"Missing required configuration keys: {missing_keys}")
            return False, missing_keys
        
        return True, []
    
    @classmethod
    def get_lightning_config(cls):
        """Get Lightning Network configuration based on API type"""
        if cls.LIGHTNING_API_TYPE == 'lnbits':
            return {
                'api_type': 'lnbits',
                'lnbits_url': cls.LNBITS_URL,
                'lnbits_admin_key': cls.LNBITS_ADMIN_KEY,
                'lnbits_wallet_key': cls.LNBITS_WALLET_KEY
            }
        elif cls.LIGHTNING_API_TYPE == 'lnd':
            return {
                'api_type': 'lnd',
                'lnd_url': cls.LND_URL,
                'lnd_macaroon': cls.LND_MACAROON,
                'lnd_skip_verify': cls.LND_SKIP_VERIFY
            }
        elif cls.LIGHTNING_API_TYPE == 'btcpay':
            return {
                'api_type': 'btcpay',
                'btcpay_url': cls.BTCPAY_URL,
                'btcpay_api_key': cls.BTCPAY_API_KEY,
                'btcpay_store_id': cls.BTCPAY_STORE_ID
            }
        else:
            return {'api_type': 'mock'}
    
    @classmethod
    def get_database_config(cls):
        """Get database configuration"""
        return {
            'database_url': cls.DATABASE_URL
        }
    
    @classmethod
    def get_openai_config(cls):
        """Get OpenAI configuration"""
        return {
            'api_key': cls.OPENAI_API_KEY,
            'model': cls.OPENAI_MODEL
        }
    
    @classmethod
    def get_africastalking_config(cls):
        """Get Africastalking configuration"""
        return {
            'username': cls.AFRICASTALKING_USERNAME,
            'api_key': cls.AFRICASTALKING_API_KEY
        }
    
    @classmethod
    def get_mpesa_config(cls):
        """Get M-Pesa configuration"""
        return {
            'consumer_key': cls.MPESA_CONSUMER_KEY,
            'consumer_secret': cls.MPESA_CONSUMER_SECRET,
            'passkey': cls.MPESA_PASSKEY,
            'shortcode': cls.MPESA_SHORTCODE
        }

# Configuration validation on import
def validate_config():
    """Validate configuration on module import"""
    valid, missing = Config.validate_required_keys()
    if not valid:
        logger.warning("=" * 50)
        logger.warning("CONFIGURATION WARNING")
        logger.warning("=" * 50)
        logger.warning(f"Missing required keys: {missing}")
        logger.warning("Please update your .env file with the correct values")
        logger.warning("=" * 50)

# Run validation
validate_config()