"""
Intersend API Client for M-Pesa STK Push Integration
Based on the Intersend PHP SDK functionality
"""
import requests
import time
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class IntersendAPIError(Exception):
    """Custom exception for Intersend API errors"""
    pass

class IntersendClient:
    """Intersend API client for payment collection and status checking"""
    
    def __init__(self, token: str = None, publishable_key: str = None, test: bool = True):
        """
        Initialize Intersend client
        
        Args:
            token: Secret key (ISSecretKey_*)
            publishable_key: Publishable key (ISPubKey_*)  
            test: Whether to use test mode
        """
        self.token = token or os.getenv('INTERSEND_SECRET_KEY')
        self.publishable_key = publishable_key or os.getenv('INTERSEND_PUBLISHABLE_KEY')
        self.test = test
        self.base_url = "https://sandbox.intasend.com" if test else "https://payment.intasend.com"
        # If using live keys, force production URL
        if self.token and self.token.startswith('ISSecretKey_live_'):
            self.base_url = "https://payment.intasend.com"
        
        if not self.token or not self.publishable_key:
            raise IntersendAPIError("Token and publishable key are required")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to Intersend API"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers)
            else:
                response = requests.get(url, headers=headers)
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Intersend API request failed: {e}")
            raise IntersendAPIError(f"API request failed: {e}")
    
    def create_collection(
        self,
        amount: float,
        phone_number: str,
        currency: str = "KES",
        method: str = "M-PESA",
        api_ref: str = "",
        name: str = "",
        email: str = ""
    ) -> Dict[str, Any]:
        """
        Create a payment collection request
        
        Args:
            amount: Payment amount
            phone_number: Customer phone number (254XXXXXXXXX format)
            currency: Payment currency (default: KES)
            method: Payment method (default: MPESA_STK_PUSH)
            api_ref: API reference for tracking
            name: Customer name
            email: Customer email
            
        Returns:
            Dict containing collection response with invoice_id
        """
        data = {
            "amount": amount,
            "phone_number": phone_number,
            "currency": currency,
            "method": method,
            "api_ref": api_ref or f"REF_{int(time.time())}",
            "name": name,
            "email": email,
            "public_key": self.publishable_key
        }
        
        logger.info(f"Creating collection for {phone_number}, amount: {amount} {currency}")
        response = self._make_request('POST', '/api/v1/payment/collection/', data)
        
        if 'invoice' in response and 'invoice_id' in response['invoice']:
            logger.info(f"Collection created successfully: {response['invoice']['invoice_id']}")
            return response
        else:
            raise IntersendAPIError(f"Invalid collection response: {response}")
    
    def check_status(self, invoice_id: str) -> Dict[str, Any]:
        """
        Check payment status by invoice ID
        
        Args:
            invoice_id: Invoice ID from create_collection
            
        Returns:
            Dict containing status information
        """
        logger.info(f"Checking status for invoice: {invoice_id}")
        # Try status endpoint similar to PHP Collection->status()
        response = self._make_request('GET', f'/api/v1/payment/collection/{invoice_id}/')
        return response
    
    def poll_status(
        self, 
        invoice_id: str, 
        max_attempts: int = 6, 
        interval: int = 10
    ) -> Dict[str, Any]:
        """
        Poll payment status until completion or failure
        
        Args:
            invoice_id: Invoice ID to poll
            max_attempts: Maximum polling attempts
            interval: Seconds between polls
            
        Returns:
            Dict with final status information
        """
        logger.info(f"Starting status polling for invoice: {invoice_id}")
        
        for attempt in range(max_attempts):
            try:
                status_response = self.check_status(invoice_id)
                
                if 'invoice' not in status_response:
                    raise IntersendAPIError("Invalid status response format")
                
                invoice = status_response['invoice']
                state = invoice.get('state', 'UNKNOWN')
                failed_reason = invoice.get('failed_reason', '')
                failed_code = invoice.get('failed_code', '')
                
                logger.info(f"Attempt {attempt + 1}/{max_attempts}: Status = {state}")
                
                if state == 'COMPLETE':
                    logger.info(f"Transaction {invoice_id} completed successfully")
                    return status_response
                elif failed_reason or failed_code:
                    logger.error(f"Transaction {invoice_id} failed: {failed_reason} (Code: {failed_code})")
                    return status_response
                
                if attempt < max_attempts - 1:
                    time.sleep(interval)
                    
            except Exception as e:
                logger.error(f"Error during status check attempt {attempt + 1}: {e}")
                if attempt == max_attempts - 1:
                    raise
                time.sleep(interval)
        
        logger.warning(f"Transaction {invoice_id} did not complete within {max_attempts} attempts")
        return self.check_status(invoice_id)


def create_intersend_client() -> IntersendClient:
    """Factory function to create Intersend client with environment variables"""
    return IntersendClient(
        token=os.getenv('INTERSEND_SECRET_KEY'),
        publishable_key=os.getenv('INTERSEND_PUBLISHABLE_KEY'),
        test=os.getenv('INTERSEND_TEST_MODE', 'true').lower() == 'true'
    )