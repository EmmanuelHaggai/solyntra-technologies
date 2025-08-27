"""
Africa's Talking Sandbox Client
Real integration with AT Sandbox for USSD testing
"""
import requests
import json
from config import Config
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AfricasTalkingSandboxClient:
    """Client for Africa's Talking Sandbox API"""
    
    def __init__(self):
        self.username = Config.AFRICASTALKING_USERNAME
        self.api_key = Config.AFRICASTALKING_API_KEY
        self.environment = Config.AFRICASTALKING_ENVIRONMENT or 'sandbox'
        
        # Sandbox URLs
        self.base_url = "https://api.sandbox.africastalking.com/version1"
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'apiKey': self.api_key
        }
    
    def create_checkout_token(self, phone_number: str) -> Dict[str, Any]:
        """Create checkout token for mobile payments"""
        try:
            url = f"{self.base_url}/mobile/checkout/token/create"
            data = {
                'username': self.username,
                'phoneNumber': phone_number
            }
            
            response = requests.post(url, headers=self.headers, data=data)
            result = response.json()
            
            logger.info(f"Checkout token creation: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating checkout token: {e}")
            return {"status": "error", "message": str(e)}
    
    def mobile_checkout(self, phone_number: str, amount: float, currency_code: str = "KES") -> Dict[str, Any]:
        """Initiate mobile checkout (M-Pesa simulation)"""
        try:
            url = f"{self.base_url}/mobile/checkout/request"
            data = {
                'username': self.username,
                'phoneNumber': phone_number,
                'currencyCode': currency_code,
                'amount': amount,
                'metadata': json.dumps({
                    'source': 'ussd_lightning_wallet',
                    'type': 'topup'
                })
            }
            
            response = requests.post(url, headers=self.headers, data=data)
            result = response.json()
            
            logger.info(f"Mobile checkout initiated: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error initiating mobile checkout: {e}")
            return {"status": "error", "message": str(e)}
    
    def mobile_payment(self, phone_number: str, amount: float, currency_code: str = "KES") -> Dict[str, Any]:
        """Send mobile payment (M-Pesa payout simulation)"""
        try:
            url = f"{self.base_url}/mobile/b2c/request"
            data = {
                'username': self.username,
                'productName': 'Lightning Wallet',
                'recipients': json.dumps([{
                    'phoneNumber': phone_number,
                    'currencyCode': currency_code,
                    'amount': amount,
                    'metadata': {
                        'source': 'ussd_lightning_wallet',
                        'type': 'withdrawal'
                    },
                    'reason': 'BusinessPayment'
                }])
            }
            
            response = requests.post(url, headers=self.headers, data=data)
            result = response.json()
            
            logger.info(f"Mobile payment sent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending mobile payment: {e}")
            return {"status": "error", "message": str(e)}
    
    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS notification"""
        try:
            url = f"{self.base_url}/messaging"
            data = {
                'username': self.username,
                'to': phone_number,
                'message': message
            }
            
            response = requests.post(url, headers=self.headers, data=data)
            result = response.json()
            
            logger.info(f"SMS sent: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        try:
            url = f"{self.base_url}/user"
            params = {'username': self.username}
            
            response = requests.get(url, headers=self.headers, params=params)
            result = response.json()
            
            logger.info(f"Account balance: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {"status": "error", "message": str(e)}

# Global client instance
at_client = AfricasTalkingSandboxClient()