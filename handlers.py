"""
Lightning Network USSD Handler Functions
Integrates MeTTa reasoning with Lightning operations
"""
import logging
from typing import Dict, Any, Tuple, Optional
from hyperon import MeTTa
from lightning import lightning_api
from intersend_helpers import initiate_mpesa_stk_push, check_mpesa_status, get_payment_summary
import time
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class USSDHandlers:
    def __init__(self, metta_file: str = "atoms.metta"):
        self.metta = MeTTa()
        self.load_knowledge_base(metta_file)
        self.sessions = {}  # Store session data
        
    def load_knowledge_base(self, metta_file: str):
        """Load MeTTa knowledge base from file"""
        try:
            with open(metta_file, 'r') as f:
                content = f.read()
                # Parse and load atoms
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith(';'):
                        try:
                            result = self.metta.run(line)
                            logger.debug(f"Loaded: {line}")
                        except Exception as e:
                            logger.warning(f"Error loading line '{line}': {e}")
        except FileNotFoundError:
            logger.error(f"MeTTa file {metta_file} not found")
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
    
    def get_user_balance(self, phone_number: str) -> int:
        """Get user balance from MeTTa and sync with Lightning API"""
        # Query MeTTa for balance
        query = f'!(match &self (Balance "{phone_number}" $b) $b)'
        try:
            result = self.metta.run(query)
            if result and len(result) > 0:
                metta_balance = int(str(result[0]).strip('[]'))
                # Sync with Lightning API balance
                lightning_balance = lightning_api.get_balance(phone_number)
                if lightning_balance != metta_balance:
                    self.update_balance(phone_number, lightning_balance)
                return lightning_balance
        except Exception as e:
            logger.error(f"Error getting balance for {phone_number}: {e}")
        
        # Fallback to Lightning API
        return lightning_api.get_balance(phone_number)
    
    def update_balance(self, phone_number: str, new_balance: int):
        """Update balance in both MeTTa and Lightning API"""
        try:
            # Remove old balance
            remove_query = f'!(remove-atom &self (Balance "{phone_number}" $b))'
            self.metta.run(remove_query)
            
            # Add new balance
            add_query = f'!(add-atom &self (Balance "{phone_number}" {new_balance}))'
            self.metta.run(add_query)
            
            # Update Lightning API
            lightning_api.set_balance(phone_number, new_balance)
            
            logger.info(f"Updated balance for {phone_number}: {new_balance} sats")
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        if not phone_number.startswith('+254'):
            if phone_number.startswith('254'):
                phone_number = '+' + phone_number
            elif phone_number.startswith('0') and len(phone_number) == 10:
                phone_number = '+254' + phone_number[1:]
            else:
                return False
        return len(phone_number) == 13 and phone_number[1:].isdigit()
    
    def normalize_phone_number(self, phone_number: str) -> str:
        """Normalize phone number to international format"""
        phone_number = phone_number.strip()
        if phone_number.startswith('0') and len(phone_number) == 10:
            return '+254' + phone_number[1:]
        elif phone_number.startswith('254') and len(phone_number) == 12:
            return '+' + phone_number
        elif phone_number.startswith('+254'):
            return phone_number
        return phone_number
    
    def validate_amount(self, amount: int) -> Tuple[bool, str]:
        """Validate transaction amount - flexible for Lightning Network micro-transactions"""
        if amount < 1:
            return False, "Minimum amount is 1 sat"
        if amount > 1000000:
            return False, "Maximum amount is 1,000,000 sats"
        return True, ""
    
    def send_btc(self, from_phone: str, to_phone: str, amount: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Send Bitcoin Lightning payment"""
        try:
            from_phone = self.normalize_phone_number(from_phone)
            to_phone = self.normalize_phone_number(to_phone)
            
            # Validate inputs
            if not self.validate_phone_number(from_phone):
                return False, "Invalid sender phone number", {}
            
            if not self.validate_phone_number(to_phone):
                return False, "Invalid recipient phone number", {}
            
            valid_amount, amount_error = self.validate_amount(amount)
            if not valid_amount:
                return False, amount_error, {}
            
            # Check sender balance
            sender_balance = self.get_user_balance(from_phone)
            if sender_balance < amount:
                return False, f"Insufficient balance. Current: {sender_balance} sats", {}
            
            # Create invoice for recipient
            success, invoice_data = lightning_api.create_invoice(to_phone, amount, f"USSD payment from {from_phone}")
            if not success:
                return False, "Failed to create payment invoice", {}
            
            # Pay the invoice
            success, payment_result = lightning_api.pay_invoice(from_phone, invoice_data["payment_request"])
            if not success:
                return False, payment_result.get("error", "Payment failed"), {}
            
            # Record transaction in MeTTa
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            transaction_atom = f'!(add-atom &self (Transaction "{from_phone}" "{to_phone}" {amount} Lightning "{timestamp}"))'
            self.metta.run(transaction_atom)
            
            # Update balances
            self.update_balance(from_phone, sender_balance - amount)
            self.update_balance(to_phone, self.get_user_balance(to_phone) + amount)
            
            return True, f"Sent {amount} sats to {to_phone}. New balance: {sender_balance - amount} sats", payment_result
            
        except Exception as e:
            logger.error(f"Error in send_btc: {e}")
            return False, "Internal error during payment", {}
    
    def receive_btc(self, phone_number: str, amount: int, memo: str = "") -> Tuple[bool, str, Dict[str, Any]]:
        """Generate Lightning invoice for receiving Bitcoin"""
        try:
            phone_number = self.normalize_phone_number(phone_number)
            
            if not self.validate_phone_number(phone_number):
                return False, "Invalid phone number", {}
            
            valid_amount, amount_error = self.validate_amount(amount)
            if not valid_amount:
                return False, amount_error, {}
            
            # Create Lightning invoice
            success, invoice_data = lightning_api.create_invoice(phone_number, amount, memo or "USSD Bitcoin payment")
            
            if success:
                # Store invoice reference in MeTTa
                timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                invoice_atom = f'!(add-atom &self (Invoice "{phone_number}" "{invoice_data["invoice_id"]}" {amount} "{timestamp}"))'
                self.metta.run(invoice_atom)
                
                # Create short invoice code for USSD display
                short_code = invoice_data["invoice_id"][-8:]  # Last 8 chars
                
                return True, f"Invoice created: {short_code}\nAmount: {amount} sats\nShare this code or pay via Lightning wallet", invoice_data
            else:
                return False, "Failed to create invoice", {}
                
        except Exception as e:
            logger.error(f"Error in receive_btc: {e}")
            return False, "Internal error creating invoice", {}
    
    def send_invoice(self, from_phone: str, to_phone: str, amount: int, memo: str = "") -> Tuple[bool, str, Dict[str, Any]]:
        """Send Lightning invoice to another user"""
        try:
            from_phone = self.normalize_phone_number(from_phone)
            to_phone = self.normalize_phone_number(to_phone)
            
            if not self.validate_phone_number(from_phone) or not self.validate_phone_number(to_phone):
                return False, "Invalid phone number", {}
            
            # Create invoice
            success, message, invoice_data = self.receive_btc(from_phone, amount, memo)
            
            if success:
                # In a real implementation, this would send SMS
                logger.info(f"Sending invoice to {to_phone}: {invoice_data['payment_request']}")
                return True, f"Invoice sent to {to_phone}\nAmount: {amount} sats", invoice_data
            else:
                return False, message, {}
                
        except Exception as e:
            logger.error(f"Error in send_invoice: {e}")
            return False, "Internal error sending invoice", {}
    
    def topup_via_mpesa(self, phone_number: str, kes_amount: int, mpesa_code: str = None) -> Tuple[bool, str, Dict[str, Any]]:
        """M-Pesa to Lightning top-up with real STK Push integration"""
        logger.info(f"MPESA_TOPUP - Starting topup for {phone_number}, amount: {kes_amount} KES")
        try:
            phone_number = self.normalize_phone_number(phone_number)
            logger.info(f"MPESA_TOPUP - Normalized phone: {phone_number}")
            
            if not self.validate_phone_number(phone_number):
                return False, "Invalid phone number", {}
            
            if kes_amount < 10:
                return False, "Minimum Lightning Network purchase is 10 KES (66 sats)", {}
            
            # Convert KES to sats (150 KES = 1000 sats)
            sats_amount = int(kes_amount * (1000 / 150))
            
            # Use Intersend M-Pesa STK Push
            reference = f"BTC_TOPUP_{int(time.time())}"
            logger.info(f"MPESA_TOPUP - Calling initiate_mpesa_stk_push")
            logger.info(f"MPESA_TOPUP - Reference: {reference}")
            
            success, response = initiate_mpesa_stk_push(
                phone_number=phone_number,
                amount=float(kes_amount),
                reference=reference
            )
            
            logger.info(f"MPESA_TOPUP - STK Push response: success={success}")
            logger.info(f"MPESA_TOPUP - STK Push data: {response}")
            
            if not success:
                logger.error(f"MPESA_TOPUP - STK Push failed: {response}")
                return False, "Failed to initiate M-Pesa payment. Please try again.", {}
            
            invoice_id = response.get('invoice', {}).get('invoice_id')
            logger.info(f"MPESA_TOPUP - Invoice ID: {invoice_id}")
            
            if not invoice_id:
                logger.error(f"MPESA_TOPUP - No invoice ID in response: {response}")
                return False, "Payment initiation failed", {}
            
            # Store pending transaction
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            pending_atom = f'!(add-atom &self (PendingMpesa "{phone_number}" "{invoice_id}" {kes_amount} {sats_amount} "{timestamp}"))'
            self.metta.run(pending_atom)
            
            return True, f"M-Pesa payment request sent to {phone_number}\nAmount: {kes_amount} KES ({sats_amount} sats)\nComplete payment on your phone to receive Bitcoin", {
                "kes_amount": kes_amount,
                "sats_amount": sats_amount,
                "invoice_id": invoice_id,
                "status": "pending_payment"
            }
            
        except Exception as e:
            import traceback
            error_details = f"Error: {str(e)} | Traceback: {traceback.format_exc()}"
            logger.error(f"Error in topup_via_mpesa: {error_details}")
            # Temporarily return detailed error for debugging
            return False, f"DEBUG ERROR: {str(e)}", {}
    
    def complete_mpesa_topup(self, invoice_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Check and complete M-Pesa payment after user confirmation"""
        try:
            # Check payment status
            status_response = check_mpesa_status(invoice_id)
            
            if 'error' in status_response:
                return False, "Unable to verify payment status", {}
            
            payment_summary = get_payment_summary(status_response)
            
            if payment_summary['status'] == 'COMPLETE':
                # Find pending transaction
                query = f'!(match &self (PendingMpesa $phone $invoice $kes $sats $timestamp) (list $phone $invoice $kes $sats $timestamp))'
                result = self.metta.run(query)
                
                for pending in result:
                    parts = str(pending).strip('[]').split()
                    if len(parts) >= 2 and parts[1].strip('"') == invoice_id:
                        phone_number = parts[0].strip('"')
                        kes_amount = int(parts[2])
                        sats_amount = int(parts[3])
                        
                        # Update balance
                        current_balance = self.get_user_balance(phone_number)
                        new_balance = current_balance + sats_amount
                        self.update_balance(phone_number, new_balance)
                        
                        # Record completed transaction
                        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                        transaction_atom = f'!(add-atom &self (Transaction "M-Pesa" "{phone_number}" {sats_amount} TopUp "{timestamp}"))'
                        self.metta.run(transaction_atom)
                        
                        # Remove pending transaction
                        remove_pending = f'!(remove-atom &self (PendingMpesa "{phone_number}" "{invoice_id}" {kes_amount} {sats_amount} $timestamp))'
                        self.metta.run(remove_pending)
                        
                        return True, f"Payment confirmed! {sats_amount} sats added to your balance.\nM-Pesa Ref: {payment_summary.get('mpesa_reference', 'N/A')}\nNew balance: {new_balance} sats", {
                            "kes_amount": kes_amount,
                            "sats_amount": sats_amount,
                            "new_balance": new_balance,
                            "mpesa_reference": payment_summary.get('mpesa_reference')
                        }
                
                return False, "Payment completed but no matching pending transaction found", {}
                
            elif payment_summary['status'] in ['FAILED', 'CANCELLED']:
                return False, f"Payment failed: {payment_summary.get('failed_reason', 'Unknown error')}", {}
            else:
                return False, f"Payment still {payment_summary['status'].lower()}. Please wait and try again.", {}
            
        except Exception as e:
            logger.error(f"Error completing M-Pesa topup: {e}")
            return False, "Error verifying payment", {}
    
    def withdraw_to_mpesa(self, phone_number: str, kes_amount: int, mpesa_number: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Simulate Lightning to M-Pesa withdrawal"""
        try:
            phone_number = self.normalize_phone_number(phone_number)
            mpesa_number = self.normalize_phone_number(mpesa_number)
            
            if not self.validate_phone_number(phone_number):
                return False, "Invalid phone number", {}
            
            if kes_amount < 100:
                return False, "Minimum withdrawal is 100 KES", {}
            
            # Convert KES to sats
            sats_amount = int(kes_amount * (1000 / 150))
            
            # Check balance
            current_balance = self.get_user_balance(phone_number)
            if current_balance < sats_amount:
                return False, f"Insufficient balance. Need {sats_amount} sats ({kes_amount} KES)", {}
            
            # Update balance
            new_balance = current_balance - sats_amount
            self.update_balance(phone_number, new_balance)
            
            # Record transaction
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            transaction_atom = f'!(add-atom &self (Transaction "{phone_number}" "M-Pesa" {sats_amount} Withdraw "{timestamp}"))'
            self.metta.run(transaction_atom)
            
            # Simulate M-Pesa payout
            logger.info(f"Simulated M-Pesa payout: {kes_amount} KES to {mpesa_number}")
            
            return True, f"Withdrew {kes_amount} KES ({sats_amount} sats) to {mpesa_number}\nNew balance: {new_balance} sats", {
                "kes_amount": kes_amount,
                "sats_amount": sats_amount,
                "new_balance": new_balance,
                "mpesa_number": mpesa_number
            }
            
        except Exception as e:
            logger.error(f"Error in withdraw_to_mpesa: {e}")
            return False, "Internal error during withdrawal", {}
    
    def get_transaction_history(self, phone_number: str, limit: int = 5) -> list:
        """Get recent transaction history"""
        try:
            phone_number = self.normalize_phone_number(phone_number)
            query = f'!(match &self (Transaction $from $to $amount $type $timestamp) (list $from $to $amount $type $timestamp))'
            result = self.metta.run(query)
            
            transactions = []
            for tx in result:
                tx_str = str(tx).strip('[]')
                parts = tx_str.split()
                if len(parts) >= 5 and (parts[0].strip('"') == phone_number or parts[1].strip('"') == phone_number):
                    transactions.append({
                        'from': parts[0].strip('"'),
                        'to': parts[1].strip('"'),
                        'amount': int(parts[2]),
                        'type': parts[3],
                        'timestamp': parts[4].strip('"')
                    })
            
            return sorted(transactions, key=lambda x: x['timestamp'], reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []
    
    def buy_airtime(self, phone_number: str, airtime_phone: str, kes_amount: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Buy airtime using Bitcoin for Kenyan mobile networks"""
        try:
            phone_number = self.normalize_phone_number(phone_number)
            airtime_phone = self.normalize_phone_number(airtime_phone)
            
            if not self.validate_phone_number(phone_number):
                return False, "Invalid sender phone number", {}
            
            if not self.validate_phone_number(airtime_phone):
                return False, "Invalid airtime recipient phone number", {}
            
            if kes_amount < 10:
                return False, "Minimum airtime purchase is 10 KES", {}
                
            if kes_amount > 1000:
                return False, "Maximum airtime purchase is 1,000 KES", {}
            
            # Convert KES to sats for balance check
            sats_needed = int(kes_amount * (1000 / 150))
            
            # Check sender balance
            sender_balance = self.get_user_balance(phone_number)
            if sender_balance < sats_needed:
                return False, f"Insufficient balance. Need {sats_needed} sats ({kes_amount} KES), have {sender_balance} sats", {}
            
            # Detect mobile network carrier
            carrier = self._detect_carrier(airtime_phone)
            
            # Simulate airtime purchase (in reality, integrate with carrier APIs)
            success = self._process_airtime_purchase(airtime_phone, kes_amount, carrier)
            
            if not success:
                return False, "Airtime purchase failed. Please try again.", {}
            
            # Deduct balance
            new_balance = sender_balance - sats_needed
            self.update_balance(phone_number, new_balance)
            
            # Record transaction
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            transaction_atom = f'!(add-atom &self (Transaction "{phone_number}" "Airtime-{carrier}" {sats_needed} Airtime "{timestamp}"))'
            self.metta.run(transaction_atom)
            
            if phone_number == airtime_phone:
                message = f"Airtime purchased successfully!\n{kes_amount} KES airtime for {carrier}\nNew balance: {new_balance} sats"
            else:
                message = f"Airtime sent successfully!\n{kes_amount} KES {carrier} airtime to {airtime_phone}\nNew balance: {new_balance} sats"
            
            return True, message, {
                "kes_amount": kes_amount,
                "sats_deducted": sats_needed,
                "carrier": carrier,
                "airtime_phone": airtime_phone,
                "new_balance": new_balance
            }
            
        except Exception as e:
            logger.error(f"Error in buy_airtime: {e}")
            return False, "Internal error during airtime purchase", {}
    
    def _detect_carrier(self, phone_number: str) -> str:
        """Detect mobile network carrier from phone number"""
        # Kenyan mobile network prefixes
        if phone_number.startswith("+254"):
            prefix = phone_number[4:7]
            
            # Safaricom prefixes
            safaricom_prefixes = ['701', '702', '703', '704', '705', '706', '707', '708', '709', 
                                '710', '711', '712', '713', '714', '715', '716', '717', '718', '719',
                                '720', '721', '722', '723', '724', '725', '726', '727', '728', '729']
            
            # Airtel prefixes  
            airtel_prefixes = ['730', '731', '732', '733', '734', '735', '736', '737', '738', '739',
                             '750', '751', '752', '753', '754', '755', '756']
            
            # Telkom prefixes
            telkom_prefixes = ['770', '771', '772', '773', '774', '775', '776', '777']
            
            if prefix in safaricom_prefixes:
                return "Safaricom"
            elif prefix in airtel_prefixes:
                return "Airtel"
            elif prefix in telkom_prefixes:
                return "Telkom"
        
        return "Unknown Carrier"
    
    def _process_airtime_purchase(self, phone_number: str, amount: int, carrier: str) -> bool:
        """Simulate airtime purchase processing"""
        # In a real implementation, this would integrate with:
        # - Safaricom API for Safaricom numbers
        # - Airtel API for Airtel numbers  
        # - Telkom API for Telkom numbers
        
        logger.info(f"Simulated airtime purchase: {amount} KES {carrier} airtime to {phone_number}")
        
        # Simulate success (in reality, this would depend on API response)
        return True
    
    def get_menu_text(self, language: str = "en") -> str:
        """Get localized main menu text"""
        if language == "sw":
            return ("Bitcoin Lightning\n"
                   "1. Tuma BTC\n"
                   "2. Pokea BTC\n"
                   "3. Tuma Ankara\n"
                   "4. Nunua BTC (M-Pesa)\n"
                   "5. Toa M-Pesa\n"
                   "6. Nunua Airtime\n"
                   "7. Historia\n"
                   "0. Ondoka")
        else:
            return ("Bitcoin Lightning\n"
                   "1. Send BTC\n"
                   "2. Receive BTC\n"
                   "3. Send Invoice\n"
                   "4. Buy BTC (M-Pesa)\n"
                   "5. Withdraw M-Pesa\n"
                   "6. Buy Airtime\n"
                   "7. History\n"
                   "0. Exit")

# Initialize handlers instance
ussd_handlers = USSDHandlers()