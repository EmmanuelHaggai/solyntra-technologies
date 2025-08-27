"""
Intersend Payment Helper Functions
Provides high-level payment operations for the USSD application
"""
import logging
from typing import Dict, Any, Optional, Tuple
from intersend_api import create_intersend_client, IntersendAPIError
import threading
import time

logger = logging.getLogger(__name__)

class IntersendPaymentHandler:
    """High-level handler for Intersend payment operations"""
    
    def __init__(self):
        self.client = create_intersend_client()
    
    def initiate_mpesa_payment(
        self,
        phone_number: str,
        amount: float,
        reference: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Initiate M-Pesa STK Push payment
        
        Args:
            phone_number: Customer phone number
            amount: Payment amount in KES
            reference: Payment reference
            
        Returns:
            Tuple of (success, response_data)
        """
        try:
            # Ensure phone number is in correct format (254XXXXXXXXX)
            formatted_phone = self._format_phone_number(phone_number)
            
            response = self.client.create_collection(
                amount=amount,
                phone_number=formatted_phone,
                currency="KES",
                method="M-PESA",
                api_ref=reference or f"USSD_{int(time.time())}",
                name="USSD User",
                email=""
            )
            
            return True, response
            
        except IntersendAPIError as e:
            logger.error(f"Intersend API error: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error initiating payment: {e}")
            return False, {"error": "Payment initiation failed"}
    
    def check_payment_status(self, invoice_id: str) -> Dict[str, Any]:
        """
        Check payment status by invoice ID
        
        Args:
            invoice_id: Invoice ID from payment initiation
            
        Returns:
            Payment status information
        """
        try:
            return self.client.check_status(invoice_id)
        except IntersendAPIError as e:
            logger.error(f"Error checking payment status: {e}")
            return {"error": str(e)}
    
    def wait_for_payment_completion(
        self,
        invoice_id: str,
        callback=None,
        max_wait_time: int = 60
    ) -> Dict[str, Any]:
        """
        Wait for payment completion with optional callback
        
        Args:
            invoice_id: Invoice ID to monitor
            callback: Optional callback function for status updates
            max_wait_time: Maximum wait time in seconds
            
        Returns:
            Final payment status
        """
        max_attempts = max_wait_time // 10  # Poll every 10 seconds
        
        try:
            result = self.client.poll_status(
                invoice_id=invoice_id,
                max_attempts=max_attempts,
                interval=10
            )
            
            if callback:
                callback(invoice_id, result)
                
            return result
            
        except IntersendAPIError as e:
            logger.error(f"Error waiting for payment completion: {e}")
            return {"error": str(e)}
    
    def process_payment_async(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        completion_callback=None
    ) -> Optional[str]:
        """
        Process payment asynchronously
        
        Args:
            phone_number: Customer phone number
            amount: Payment amount
            reference: Payment reference
            completion_callback: Callback for when payment completes
            
        Returns:
            Invoice ID if initiation successful, None otherwise
        """
        # Initiate payment
        success, response = self.initiate_mpesa_payment(phone_number, amount, reference)
        
        if not success:
            logger.error(f"Failed to initiate payment: {response}")
            return None
        
        invoice_id = response.get('invoice', {}).get('invoice_id')
        if not invoice_id:
            logger.error("No invoice ID in response")
            return None
        
        # Start background monitoring if callback provided
        if completion_callback:
            def monitor_payment():
                result = self.wait_for_payment_completion(invoice_id, completion_callback)
                logger.info(f"Payment monitoring completed for {invoice_id}: {result.get('invoice', {}).get('state', 'Unknown')}")
            
            monitor_thread = threading.Thread(target=monitor_payment)
            monitor_thread.daemon = True
            monitor_thread.start()
        
        return invoice_id
    
    def _format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number to Kenya format (254XXXXXXXXX)
        
        Args:
            phone_number: Input phone number
            
        Returns:
            Formatted phone number
        """
        # Remove any spaces, dashes, or special characters
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different input formats
        if cleaned.startswith('254'):
            return cleaned
        elif cleaned.startswith('0'):
            return '254' + cleaned[1:]
        elif len(cleaned) == 9:
            return '254' + cleaned
        else:
            # Return as-is and let API handle validation
            return cleaned


def create_payment_handler() -> IntersendPaymentHandler:
    """Factory function to create payment handler"""
    return IntersendPaymentHandler()


# Convenience functions for common operations
def initiate_mpesa_stk_push(phone_number: str, amount: float, reference: str = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to initiate M-Pesa STK Push
    
    Args:
        phone_number: Customer phone number
        amount: Payment amount in KES
        reference: Optional payment reference
        
    Returns:
        Tuple of (success, response_data)
    """
    handler = create_payment_handler()
    return handler.initiate_mpesa_payment(phone_number, amount, reference)


def check_mpesa_status(invoice_id: str) -> Dict[str, Any]:
    """
    Convenience function to check M-Pesa payment status
    
    Args:
        invoice_id: Invoice ID to check
        
    Returns:
        Payment status information
    """
    handler = create_payment_handler()
    return handler.check_payment_status(invoice_id)


def get_payment_summary(status_response: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract key payment information from status response
    
    Args:
        status_response: Response from status check
        
    Returns:
        Simplified payment summary
    """
    if 'invoice' not in status_response:
        return {"status": "error", "message": "Invalid response"}
    
    invoice = status_response['invoice']
    
    return {
        "invoice_id": invoice.get('invoice_id', ''),
        "status": invoice.get('state', 'unknown'),
        "amount": str(invoice.get('value', 0)),
        "currency": invoice.get('currency', 'KES'),
        "mpesa_reference": invoice.get('mpesa_reference', ''),
        "failed_reason": invoice.get('failed_reason', ''),
        "failed_code": invoice.get('failed_code', ''),
        "account": invoice.get('account', ''),
        "created_at": invoice.get('created_at', ''),
        "updated_at": invoice.get('updated_at', '')
    }