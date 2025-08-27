"""
USSD Handler Integration Example
Demonstrates how to integrate the MySQL database layer with your existing 
Africastalking USSD Bitcoin Lightning Network application.
"""

from flask import Flask, request
import logging
from datetime import datetime

# Import our database helper modules
from database import db_manager, init_database, check_database_health
from user_helpers import UserManager
from session_helpers import UssdSessionManager
from transaction_helpers import (
    TransactionManager, send_btc_with_logging, topup_mpesa_with_logging, 
    withdraw_mpesa_with_logging, InsufficientBalanceError
)
from invoice_helpers import InvoiceManager, send_invoice_with_logging, check_invoice_payment

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class UssdMenuStates:
    """USSD menu state constants"""
    MAIN_MENU = "main_menu"
    SEND_BTC = "send_btc"
    SEND_AMOUNT = "send_amount" 
    SEND_CONFIRM = "send_confirm"
    RECEIVE_BTC = "receive_btc"
    GENERATE_INVOICE = "generate_invoice"
    INVOICE_AMOUNT = "invoice_amount"
    TOPUP_MPESA = "topup_mpesa"
    TOPUP_AMOUNT = "topup_amount"
    TOPUP_CONFIRM = "topup_confirm"
    WITHDRAW_MPESA = "withdraw_mpesa"
    WITHDRAW_AMOUNT = "withdraw_amount"
    CHECK_BALANCE = "check_balance"
    TRANSACTION_HISTORY = "transaction_history"

class UssdHandler:
    """
    USSD Handler class that integrates with MySQL database.
    This replaces or enhances your existing USSD handler.
    """
    
    def __init__(self):
        # Initialize database on startup
        try:
            if not check_database_health():
                logger.error("Database not accessible, initializing...")
                init_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    
    def handle_ussd_request(self, session_id: str, phone_number: str, text: str) -> str:
        """
        Main USSD request handler with database integration.
        
        Args:
            session_id: Africastalking session ID
            phone_number: User's phone number
            text: User input text
            
        Returns:
            USSD response text
        """
        try:
            # Create or get user in database
            user, created = UserManager.create_or_get_user(phone_number)
            if created:
                logger.info(f"New user registered: {phone_number}")
            
            # Get or create USSD session
            ussd_session = UssdSessionManager.get_session(session_id)
            if not ussd_session:
                # Create new session starting at main menu
                ussd_session = UssdSessionManager.create_or_update_session(
                    session_id, phone_number, UssdMenuStates.MAIN_MENU
                )
            
            # Parse user input
            user_input = text.split('*')[-1] if text else ""
            
            # Route to appropriate handler based on current state
            current_state = ussd_session.current_state
            
            if current_state == UssdMenuStates.MAIN_MENU:
                return self._handle_main_menu(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.SEND_BTC:
                return self._handle_send_btc(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.SEND_AMOUNT:
                return self._handle_send_amount(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.SEND_CONFIRM:
                return self._handle_send_confirm(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.GENERATE_INVOICE:
                return self._handle_generate_invoice(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.INVOICE_AMOUNT:
                return self._handle_invoice_amount(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.TOPUP_AMOUNT:
                return self._handle_topup_amount(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.TOPUP_CONFIRM:
                return self._handle_topup_confirm(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.WITHDRAW_AMOUNT:
                return self._handle_withdraw_amount(session_id, phone_number, user_input)
            elif current_state == UssdMenuStates.CHECK_BALANCE:
                return self._handle_check_balance(session_id, phone_number)
            elif current_state == UssdMenuStates.TRANSACTION_HISTORY:
                return self._handle_transaction_history(session_id, phone_number)
            else:
                # Unknown state, reset to main menu
                return self._handle_main_menu(session_id, phone_number, "")
                
        except Exception as e:
            logger.error(f"USSD handler error: {e}")
            return "END Service temporarily unavailable. Please try again later."
    
    def _handle_main_menu(self, session_id: str, phone_number: str, user_input: str) -> str:
        """Handle main menu interactions"""
        try:
            if user_input == "":
                # First visit - show main menu
                user_balance = UserManager.get_user_balance(phone_number)
                balance_text = f"Balance: {user_balance:,} sats" if user_balance is not None else "Balance: 0 sats"
                
                menu_text = f"CON Lightning Wallet\\n{balance_text}\\n\\n"
                menu_text += "1. Send Bitcoin\\n"
                menu_text += "2. Receive Bitcoin\\n" 
                menu_text += "3. Generate Invoice\\n"
                menu_text += "4. Buy Bitcoin (M-Pesa → Lightning)\\n"
                menu_text += "5. Withdraw (M-Pesa)\\n"
                menu_text += "6. Check Balance\\n"
                menu_text += "7. Transaction History"
                
                return menu_text
            
            # Handle menu selection
            elif user_input == "1":
                UssdSessionManager.update_session_state(session_id, UssdMenuStates.SEND_BTC)
                return "CON Send Bitcoin\\n\\nEnter recipient phone number:"
            
            elif user_input == "2":
                return self._handle_receive_btc(session_id, phone_number)
            
            elif user_input == "3":
                UssdSessionManager.update_session_state(session_id, UssdMenuStates.GENERATE_INVOICE)
                return "CON Generate Invoice\\n\\nEnter amount in sats:"
            
            elif user_input == "4":
                UssdSessionManager.update_session_state(session_id, UssdMenuStates.TOPUP_AMOUNT)
                return "CON Lightning Network Top-up\\n\\nBuy Bitcoin via M-Pesa\\nEnter amount in KES:"
            
            elif user_input == "5":
                UssdSessionManager.update_session_state(session_id, UssdMenuStates.WITHDRAW_AMOUNT)
                return "CON M-Pesa Withdrawal\\n\\nEnter amount in sats:"
            
            elif user_input == "6":
                return self._handle_check_balance(session_id, phone_number)
            
            elif user_input == "7":
                return self._handle_transaction_history(session_id, phone_number)
            
            else:
                return "CON Invalid option. Please try again.\\n\\n0. Back to main menu"
                
        except Exception as e:
            logger.error(f"Main menu handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_send_btc(self, session_id: str, phone_number: str, user_input: str) -> str:
        """Handle send bitcoin flow"""
        try:
            if not user_input.strip():
                return "CON Please enter a valid phone number:"
            
            # Store recipient and move to amount input
            UssdSessionManager.add_to_input_buffer(session_id, "recipient_phone", user_input)
            UssdSessionManager.update_session_state(session_id, UssdMenuStates.SEND_AMOUNT)
            
            return "CON Enter amount in sats to send:"
            
        except Exception as e:
            logger.error(f"Send BTC handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_send_amount(self, session_id: str, phone_number: str, user_input: str) -> str:
        """Handle send amount input"""
        try:
            try:
                amount_sats = int(user_input)
                if amount_sats <= 0:
                    return "CON Invalid amount. Please enter a positive number:"
            except ValueError:
                return "CON Invalid amount. Please enter a number:"
            
            # Check if user has sufficient balance
            user_balance = UserManager.get_user_balance(phone_number)
            if user_balance is None or user_balance < amount_sats:
                return f"END Insufficient balance. Available: {user_balance or 0} sats"
            
            # Store amount and show confirmation
            UssdSessionManager.add_to_input_buffer(session_id, "amount_sats", amount_sats)
            UssdSessionManager.update_session_state(session_id, UssdMenuStates.SEND_CONFIRM)
            
            buffer = UssdSessionManager.get_input_buffer(session_id)
            recipient = buffer.get("recipient_phone", "Unknown")
            
            confirm_text = f"CON Confirm Transaction:\\n\\n"
            confirm_text += f"To: {recipient}\\n"
            confirm_text += f"Amount: {amount_sats:,} sats\\n\\n"
            confirm_text += "1. Confirm\\n0. Cancel"
            
            return confirm_text
            
        except Exception as e:
            logger.error(f"Send amount handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_send_confirm(self, session_id: str, phone_number: str, user_input: str) -> str:
        """Handle send confirmation"""
        try:
            if user_input == "1":
                # Execute the transaction
                buffer = UssdSessionManager.get_input_buffer(session_id)
                recipient_phone = buffer.get("recipient_phone")
                amount_sats = buffer.get("amount_sats")
                
                if not recipient_phone or not amount_sats:
                    return "END Transaction data missing. Please try again."
                
                try:
                    # Use the database-integrated send function
                    transaction = send_btc_with_logging(
                        phone_number, recipient_phone, amount_sats
                    )
                    
                    if transaction:
                        # End session after successful transaction
                        UssdSessionManager.end_session(session_id)
                        return f"END Transaction successful!\\nSent {amount_sats:,} sats to {recipient_phone}"
                    else:
                        return "END Transaction failed. Please try again."
                        
                except InsufficientBalanceError as e:
                    return f"END {str(e)}"
                    
            elif user_input == "0":
                # Cancel transaction
                UssdSessionManager.end_session(session_id)
                return "END Transaction cancelled."
            else:
                return "CON Invalid option.\\n1. Confirm\\n0. Cancel"
                
        except Exception as e:
            logger.error(f"Send confirm handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_receive_btc(self, session_id: str, phone_number: str) -> str:
        """Handle receive bitcoin - show Lightning node info"""
        try:
            # In a real implementation, you would get this from your Lightning node
            # For now, we'll show placeholder info
            receive_text = "END Receive Bitcoin\\n\\n"
            receive_text += "Lightning Address:\\nlightning@yourdomain.com\\n\\n"
            receive_text += "Or generate an invoice using option 3 from main menu."
            
            return receive_text
            
        except Exception as e:
            logger.error(f"Receive BTC handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_generate_invoice(self, session_id: str, phone_number: str, user_input: str) -> str:
        """Handle invoice generation"""
        try:
            try:
                amount_sats = int(user_input)
                if amount_sats <= 0:
                    return "CON Invalid amount. Please enter a positive number:"
            except ValueError:
                return "CON Invalid amount. Please enter a number:"
            
            # Generate invoice using our database helpers
            invoice_string = send_invoice_with_logging(
                phone_number, amount_sats, f"Invoice for {amount_sats} sats"
            )
            
            if invoice_string:
                UssdSessionManager.end_session(session_id)
                return f"END Invoice Generated\\n\\n{invoice_string}\\n\\nAmount: {amount_sats:,} sats"
            else:
                return "END Failed to generate invoice. Please try again."
                
        except Exception as e:
            logger.error(f"Generate invoice handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_topup_amount(self, session_id: str, phone_number: str, user_input: str) -> str:
        """Handle M-Pesa topup amount input"""
        try:
            try:
                amount_kes = float(user_input)
                if amount_kes <= 0:
                    return "CON Invalid amount. Please enter a positive number:"
            except ValueError:
                return "CON Invalid amount. Please enter a number:"
            
            # Lightning Network minimum amount validation (allowing micro-purchases)
            if amount_kes < 10:
                return "CON Minimum Lightning purchase is 10 KES (66 sats). Please enter a valid amount:"
            
            # M-Pesa maximum amount validation (daily limit)
            if amount_kes > 70000:
                return "CON Maximum topup is 70,000 KES. Please enter a smaller amount:"
            
            # Convert KES to sats (example rate: 1 KES = 100 sats)
            # In production, use real exchange rates
            amount_sats = int(amount_kes * 100)
            
            # Confirm transaction details before processing
            confirm_text = f"CON Lightning Network Purchase:\\n\\n"
            confirm_text += f"Pay: {amount_kes:,.0f} KES via M-Pesa\\n"
            confirm_text += f"Receive: {amount_sats:,} sats (Lightning)\\n"
            confirm_text += f"From: {phone_number}\\n\\n"
            confirm_text += "1. Confirm & Pay\\n0. Cancel"
            
            # Store amount for confirmation step
            UssdSessionManager.add_to_input_buffer(session_id, "topup_amount_kes", amount_kes)
            UssdSessionManager.add_to_input_buffer(session_id, "topup_amount_sats", amount_sats)
            UssdSessionManager.update_session_state(session_id, UssdMenuStates.TOPUP_CONFIRM)
            
            return confirm_text
                
        except Exception as e:
            logger.error(f"Topup amount handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_topup_confirm(self, session_id: str, phone_number: str, user_input: str) -> str:
        """Handle M-Pesa topup confirmation"""
        try:
            if user_input == "1":
                # Execute the M-Pesa payment
                buffer = UssdSessionManager.get_input_buffer(session_id)
                amount_kes = buffer.get("topup_amount_kes")
                amount_sats = buffer.get("topup_amount_sats")
                
                if not amount_kes or not amount_sats:
                    return "END Transaction data missing. Please try again."
                
                try:
                    # In production, initiate M-Pesa STK push here
                    # For now, simulate successful M-Pesa payment processing
                    from intersend_helpers import initiate_mpesa_stk_push
                    
                    # Use the phone number from the USSD session (not input buffer)
                    mpesa_result = initiate_mpesa_stk_push(
                        phone_number=phone_number,  # Use USSD session phone number
                        amount=amount_kes,
                        reference=f"BTC_PURCHASE_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    )
                    
                    if mpesa_result.get('success', False):
                        # Log the transaction in database
                        transaction = topup_mpesa_with_logging(
                            phone_number, amount_sats, mpesa_result.get('transaction_id', 'PENDING')
                        )
                        
                        if transaction:
                            UssdSessionManager.end_session(session_id)
                            return f"END Lightning Network Payment Initiated!\\n\\nCHECK YOUR PHONE:\\nYou will receive an M-Pesa STK push on {phone_number}\\n\\nEnter your M-Pesa PIN to complete the payment of {amount_kes:,.0f} KES\\n\\nOnce completed: {amount_sats:,} sats will be added to your Lightning wallet."
                        else:
                            return "END Transaction logging failed. Please try again."
                    else:
                        return f"END M-Pesa payment failed: {mpesa_result.get('error', 'Unknown error')}"
                        
                except Exception as payment_error:
                    logger.error(f"M-Pesa payment error: {payment_error}")
                    # Fallback to simulation for demo
                    transaction = topup_mpesa_with_logging(
                        phone_number, amount_sats, f"DEMO_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    )
                    
                    if transaction:
                        UssdSessionManager.end_session(session_id)
                        return f"END [DEMO] Lightning Network Payment!\\n\\nCHECK YOUR PHONE:\\nYou should receive an M-Pesa STK push on {phone_number}\\n\\nEnter your M-Pesa PIN to complete the payment of {amount_kes:,.0f} KES\\n\\nOnce completed: {amount_sats:,} sats will be added to your Lightning wallet."
                    else:
                        return "END Topup failed. Please try again."
                    
            elif user_input == "0":
                # Cancel transaction
                UssdSessionManager.end_session(session_id)
                return "END Transaction cancelled."
            else:
                return "CON Invalid option.\\n1. Confirm & Pay\\n0. Cancel"
                
        except Exception as e:
            logger.error(f"Topup confirm handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_withdraw_amount(self, session_id: str, phone_number: str, user_input: str) -> str:
        """Handle M-Pesa withdrawal amount input"""
        try:
            try:
                amount_sats = int(user_input)
                if amount_sats <= 0:
                    return "CON Invalid amount. Please enter a positive number:"
            except ValueError:
                return "CON Invalid amount. Please enter a number:"
            
            # Check balance
            user_balance = UserManager.get_user_balance(phone_number)
            if user_balance is None or user_balance < amount_sats:
                return f"END Insufficient balance. Available: {user_balance or 0} sats"
            
            try:
                # Execute withdrawal with database logging
                transaction = withdraw_mpesa_with_logging(phone_number, amount_sats)
                
                if transaction:
                    UssdSessionManager.end_session(session_id)
                    # Convert sats to KES for display
                    amount_kes = amount_sats / 100
                    return f"END Withdrawal initiated!\\n\\n{amount_sats:,} sats (≈{amount_kes:.2f} KES)\\nM-Pesa will be sent to {phone_number}"
                else:
                    return "END Withdrawal failed. Please try again."
                    
            except InsufficientBalanceError as e:
                return f"END {str(e)}"
                
        except Exception as e:
            logger.error(f"Withdraw amount handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_check_balance(self, session_id: str, phone_number: str) -> str:
        """Handle balance check"""
        try:
            user_balance = UserManager.get_user_balance(phone_number)
            balance_kes = (user_balance / 100) if user_balance else 0
            
            balance_text = f"END Current Balance\\n\\n"
            balance_text += f"{user_balance or 0:,} sats\\n"
            balance_text += f"≈{balance_kes:.2f} KES"
            
            return balance_text
            
        except Exception as e:
            logger.error(f"Check balance handler error: {e}")
            return "END Service error. Please try again."
    
    def _handle_transaction_history(self, session_id: str, phone_number: str) -> str:
        """Handle transaction history display"""
        try:
            transactions = TransactionManager.get_user_transactions(phone_number, limit=5)
            
            if not transactions:
                return "END No transaction history found."
            
            history_text = "END Recent Transactions\\n\\n"
            
            for tx in transactions:
                date_str = tx.created_at.strftime("%m/%d %H:%M")
                status_icon = "✓" if tx.status == "completed" else "⏳" if tx.status == "pending" else "✗"
                
                if tx.transaction_type == "send":
                    history_text += f"{status_icon} -{tx.amount_sats:,} sats ({date_str})\\n"
                elif tx.transaction_type == "receive":
                    history_text += f"{status_icon} +{tx.amount_sats:,} sats ({date_str})\\n"
                elif tx.transaction_type == "topup":
                    history_text += f"{status_icon} Topup +{tx.amount_sats:,} sats ({date_str})\\n"
                elif tx.transaction_type == "withdraw":
                    history_text += f"{status_icon} Withdrawal -{tx.amount_sats:,} sats ({date_str})\\n"
                else:
                    history_text += f"{status_icon} {tx.transaction_type.title()} {tx.amount_sats:,} sats ({date_str})\\n"
            
            return history_text
            
        except Exception as e:
            logger.error(f"Transaction history handler error: {e}")
            return "END Service error. Please try again."

# Flask route for Africastalking USSD webhook
@app.route('/ussd', methods=['POST'])
def ussd_callback():
    """
    Africastalking USSD webhook endpoint.
    This is where Africastalking sends USSD requests.
    """
    try:
        # Get parameters from Africastalking
        session_id = request.values.get('sessionId')
        service_code = request.values.get('serviceCode') 
        phone_number = request.values.get('phoneNumber')
        text = request.values.get('text', '')
        
        logger.info(f"USSD request: {phone_number}, session: {session_id}, text: '{text}'")
        
        # Initialize USSD handler and process request
        handler = UssdHandler()
        response = handler.handle_ussd_request(session_id, phone_number, text)
        
        logger.info(f"USSD response: {response}")
        return response
        
    except Exception as e:
        logger.error(f"USSD callback error: {e}")
        return "END Service temporarily unavailable. Please try again later."

# Background tasks for maintenance
def cleanup_expired_data():
    """
    Background task to clean up expired sessions and invoices.
    Run this periodically (e.g., every hour) as a cron job or scheduled task.
    """
    try:
        # Cleanup expired USSD sessions (older than 30 minutes)
        expired_sessions = UssdSessionManager.cleanup_expired_sessions(30)
        logger.info(f"Cleaned up {expired_sessions} expired USSD sessions")
        
        # Cleanup expired invoices
        expired_invoices = InvoiceManager.cleanup_expired_invoices()
        logger.info(f"Cleaned up {expired_invoices} expired invoices")
        
    except Exception as e:
        logger.error(f"Cleanup task error: {e}")

if __name__ == '__main__':
    # Database setup
    try:
        init_database()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        exit(1)
    
    # Start Flask app for USSD webhook
    print("Starting USSD service...")
    print("Make sure to:")
    print("1. Update DATABASE_URL in database.py with your MySQL credentials")
    print("2. Configure Africastalking webhook URL to point to /ussd endpoint")
    print("3. Set up periodic cleanup_expired_data() calls")
    print("4. Replace placeholder Lightning operations with real implementations")
    
    app.run(debug=False, host='0.0.0.0', port=5000)