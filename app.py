"""
Flask USSD Application for Bitcoin Lightning Network
Integrates with Africa's Talking USSD API and MeTTa reasoning
Unified version with all features
"""
from flask import Flask, request, jsonify, render_template_string, send_file
import logging
from handlers import USSDHandlers
from lightning import lightning_api
import re
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

# Configure comprehensive logging
import sys
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# Enable Flask request logging
logging.getLogger('werkzeug').setLevel(logging.DEBUG)

# Ensure unbuffered output
sys.stdout.flush()
sys.stderr.flush()

app = Flask(__name__)

# Initialize handlers
ussd_handlers = USSDHandlers()

# Session storage (in production, use Redis or database)
user_sessions = {}

class USSDSession:
    def __init__(self, session_id: str, phone_number: str):
        self.session_id = session_id
        self.phone_number = phone_number
        self.state = "main_menu"
        self.data = {}
    
    def set_state(self, state: str):
        self.state = state
    
    def set_data(self, key: str, value):
        self.data[key] = value
    
    def get_data(self, key: str, default=None):
        return self.data.get(key, default)

def get_or_create_session(session_id: str, phone_number: str) -> USSDSession:
    """Get existing session or create new one"""
    if session_id not in user_sessions:
        user_sessions[session_id] = USSDSession(session_id, phone_number)
    return user_sessions[session_id]

def clear_session(session_id: str):
    """Clear session data"""
    if session_id in user_sessions:
        del user_sessions[session_id]

@app.route('/ussd', methods=['POST'])
def ussd():
    """Main USSD endpoint for Africa's Talking"""
    request_id = f"req_{int(time.time())}_{hash(request.remote_addr) % 10000}"
    
    try:
        # Log complete request details
        print(f"DEBUG: USSD Request received - Phone: {request.values.get('phoneNumber', 'Unknown')}", flush=True)
        sys.stdout.flush()
        logger.info(f"[{request_id}] ===== NEW USSD REQUEST =====")
        logger.info(f"[{request_id}] Remote IP: {request.remote_addr}")
        logger.info(f"[{request_id}] User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        logger.info(f"[{request_id}] Content-Type: {request.headers.get('Content-Type', 'Unknown')}")
        logger.info(f"[{request_id}] Method: {request.method}")
        logger.info(f"[{request_id}] Full URL: {request.url}")
        
        # Get Africa's Talking parameters
        session_id = request.values.get("sessionId", "")
        service_code = request.values.get("serviceCode", "")
        phone_number = request.values.get("phoneNumber", "")
        text = request.values.get("text", "")
        
        # Log all request parameters
        logger.info(f"[{request_id}] Session ID: '{session_id}'")
        logger.info(f"[{request_id}] Service Code: '{service_code}'")
        logger.info(f"[{request_id}] Phone Number: '{phone_number}'")
        logger.info(f"[{request_id}] Text Input: '{text}'")
        logger.info(f"[{request_id}] Text Length: {len(text)}")
        logger.info(f"[{request_id}] Text Repr: {repr(text)}")
        logger.info(f"[{request_id}] All Form Data: {dict(request.values)}")
        logger.info(f"[{request_id}] Current Active Sessions: {len(user_sessions)}")
        logger.info(f"[{request_id}] Session Exists: {session_id in user_sessions}")
        
        # Get or create session
        session = get_or_create_session(session_id, phone_number)
        
        # Initialize user balance for your number
        if phone_number == "+254715586044":
            current_balance = ussd_handlers.get_user_balance(phone_number)
            if current_balance == 0:
                lightning_api.set_balance(phone_number, 0)
                ussd_handlers.update_balance(phone_number, 0)
        
        # Parse text input (split by *)
        text_parts = text.split("*") if text else [""]
        logger.info(f"Text parts: {text_parts}")
        logger.info(f"Session state: {session.state}")
        
        # Route based on session state and input
        logger.info(f"[{request_id}] Routing request - Text empty: {text == ''}")
        
        if text == "":
            # First interaction - show main menu
            logger.info(f"[{request_id}] Showing main menu")
            response = handle_main_menu(session)
        else:
            logger.info(f"[{request_id}] Processing user input with text_parts: {text_parts}")
            response = handle_user_input(session, text_parts)
        
        logger.info(f"[{request_id}] USSD Response: {response}")
        logger.info(f"[{request_id}] Response Length: {len(response)}")
        logger.info(f"[{request_id}] ===== REQUEST COMPLETED =====")
        return response
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[{request_id}] USSD EXCEPTION: {str(e)}")
        logger.error(f"[{request_id}] FULL TRACEBACK: {error_details}")
        logger.error(f"[{request_id}] ===== REQUEST FAILED =====")
        return "END Internal error. Please try again."

def handle_main_menu(session: USSDSession) -> str:
    """Handle main menu display"""
    balance = ussd_handlers.get_user_balance(session.phone_number)
    
    return (f"CON Welcome to Bitcoin Lightning!\n"
           f"₿ Balance: {balance:,} sats\n\n"
           f"Bitcoin Lightning\n"
           f"1. Send BTC\n"
           f"2. Receive BTC\n"
           f"3. Send Invoice\n"
           f"4. Buy BTC (M-Pesa)\n"
           f"5. Top Up M-Pesa\n"
           f"6. Withdraw M-Pesa\n"
           f"7. Buy Airtime\n"
           f"0. Exit")

def handle_user_input(session: USSDSession, text_parts: list) -> str:
    """Handle user input based on current state"""
    try:
        # Handle multi-step USSD input by processing each step sequentially
        if len(text_parts) > 1 and session.state == "main_menu":
            menu_selection = text_parts[0]
            logger.info(f"Multi-step input detected: menu={menu_selection}, data={text_parts[1:]}")
            
            if menu_selection == "4":  # Buy BTC via M-Pesa
                session.set_state("topup_amount")
                amount_input = text_parts[1]
                logger.info(f"Multi-step M-Pesa: processing amount '{amount_input}'")
                return handle_topup_amount(session, amount_input)
            elif menu_selection == "1":  # Send BTC
                session.set_state("send_btc_phone")
                phone_input = text_parts[1]
                return handle_send_btc_phone(session, phone_input)
            elif menu_selection == "2":  # Receive BTC
                session.set_state("receive_btc_amount")
                amount_input = text_parts[1]
                return handle_receive_btc_amount(session, amount_input)
            elif menu_selection == "3":  # Send Invoice
                session.set_state("send_invoice_phone")
                phone_input = text_parts[1]
                return handle_send_invoice_phone(session, phone_input)
            elif menu_selection == "6":  # Withdraw to M-Pesa
                session.set_state("withdraw_amount")
                amount_input = text_parts[1]
                return handle_withdraw_amount(session, amount_input)
            elif menu_selection == "7":  # Buy Airtime
                session.set_state("airtime_amount")
                amount_input = text_parts[1]
                return handle_airtime_amount(session, amount_input)
            else:
                current_input = text_parts[-1]
                return handle_main_menu_selection(session, current_input, text_parts)
        
        current_input = text_parts[-1] if text_parts else ""
        
        # Special handling: If we get 4*10 pattern but session state is lost, handle it correctly
        if (len(text_parts) == 2 and text_parts[0] == "4" and 
            text_parts[1].isdigit() and session.state == "main_menu"):
            logger.info(f"Session state recovery: treating {text} as M-Pesa amount input")
            session.set_state("topup_amount")
            return handle_topup_amount(session, text_parts[1])
        
        if session.state == "main_menu":
            return handle_main_menu_selection(session, current_input, text_parts)
        elif session.state == "send_btc_phone":
            return handle_send_btc_phone(session, current_input)
        elif session.state == "send_btc_amount":
            return handle_send_btc_amount(session, current_input)
        elif session.state == "receive_btc_amount":
            return handle_receive_btc_amount(session, current_input)
        elif session.state == "send_invoice_phone":
            return handle_send_invoice_phone(session, current_input)
        elif session.state == "send_invoice_amount":
            return handle_send_invoice_amount(session, current_input)
        elif session.state == "topup_amount":
            return handle_topup_amount(session, current_input)
        elif session.state == "withdraw_amount":
            return handle_withdraw_amount(session, current_input)
        elif session.state == "withdraw_phone":
            return handle_withdraw_phone(session, current_input)
        elif session.state == "airtime_amount":
            return handle_airtime_amount(session, current_input)
        elif session.state == "airtime_phone":
            return handle_airtime_phone(session, current_input)
        else:
            # Reset to main menu on unknown state
            session.set_state("main_menu")
            return handle_main_menu(session)
            
    except Exception as e:
        logger.error(f"Input handling error: {e}")
        clear_session(session.session_id)
        return "END Error processing request. Please try again."

def handle_main_menu_selection(session: USSDSession, selection: str, text_parts: list) -> str:
    """Handle main menu selection"""
    # Special case: Handle 4*amount pattern directly (when session state is lost)
    if len(text_parts) == 2 and text_parts[0] == "4" and text_parts[1].isdigit():
        logger.info(f"Direct M-Pesa pattern detected: {text_parts}")
        session.set_state("topup_amount")
        return handle_topup_amount(session, text_parts[1])
    
    # Handle special commands
    if selection.lower() in ['rates?', 'rates']:
        return "END Current rate: 1 KES ≈ 6.67 sats\n150 KES = 1,000 sats"
    elif selection.lower() in ['help']:
        return ("END USSD Commands:\n"
               "• Send: '1*phone*amount'\n"
               "• Buy BTC: '4*amount_kes'\n"
               "• Rates: 'rates?'\n"
               "• Help: 'help'")
    
    if selection == "1":
        # Send BTC
        session.set_state("send_btc_phone")
        return "CON Send BTC\nEnter recipient phone number:"
    elif selection == "2":
        # Receive BTC
        session.set_state("receive_btc_amount")
        return "CON Receive BTC\nEnter amount in sats:"
    elif selection == "3":
        # Send Invoice
        session.set_state("send_invoice_phone")
        return "CON Send Invoice\nEnter recipient phone number:"
    elif selection == "4":
        # Buy BTC via M-Pesa STK Push
        session.set_state("topup_amount")
        return ("CON Buy BTC with M-Pesa\n"
               "Enter KES amount (Min: 10 KES):\n\n"
               "(Ask 'rates?' or say 'back')")
    elif selection == "5":
        # Top Up M-Pesa (duplicate of 4 for compatibility)
        session.set_state("topup_amount")
        return ("CON Buy BTC with M-Pesa\n"
               "Enter KES amount (Min: 10 KES):\n\n"
               "(Ask 'rates?' or say 'back')")
    elif selection == "6":
        # Withdraw to M-Pesa
        session.set_state("withdraw_amount")
        return "CON Withdraw to M-Pesa\nEnter amount in KES:"
    elif selection == "7":
        # Buy Airtime
        session.set_state("airtime_amount")
        return "CON Buy Airtime\nEnter amount in KES (10-1000):"
    elif selection == "0":
        # Exit
        clear_session(session.session_id)
        return "END Thank you for using Bitcoin Lightning!"
    else:
        # Invalid selection
        return handle_main_menu(session)

def handle_send_btc_phone(session: USSDSession, phone_input: str) -> str:
    """Handle phone number input for sending BTC"""
    if phone_input.lower() == 'back':
        session.set_state("main_menu")
        return handle_main_menu(session)
        
    normalized_phone = ussd_handlers.normalize_phone_number(phone_input)
    
    if not ussd_handlers.validate_phone_number(normalized_phone):
        return "CON Invalid phone number format.\nEnter recipient phone number:"
    
    session.set_data("recipient_phone", normalized_phone)
    session.set_state("send_btc_amount")
    return f"CON Send BTC to {normalized_phone}\nEnter amount in sats:"

def handle_send_btc_amount(session: USSDSession, amount_input: str) -> str:
    """Handle amount input for sending BTC"""
    try:
        if amount_input.lower() == 'back':
            session.set_state("send_btc_phone")
            return "CON Send BTC\nEnter recipient phone number:"
            
        amount = int(amount_input)
        recipient_phone = session.get_data("recipient_phone")
        
        # Validate amount
        valid, error_msg = ussd_handlers.validate_amount(amount)
        if not valid:
            return f"CON {error_msg}\nEnter amount in sats:"
        
        # Execute payment
        success, message, payment_data = ussd_handlers.send_btc(session.phone_number, recipient_phone, amount)
        
        clear_session(session.session_id)
        
        if success:
            return f"END {message}"
        else:
            return f"END Payment failed: {message}"
            
    except ValueError:
        return "CON Invalid amount. Enter amount in sats:"

def handle_receive_btc_amount(session: USSDSession, amount_input: str) -> str:
    """Handle amount input for receiving BTC"""
    try:
        if amount_input.lower() == 'back':
            session.set_state("main_menu")
            return handle_main_menu(session)
            
        amount = int(amount_input)
        
        # Validate amount
        valid, error_msg = ussd_handlers.validate_amount(amount)
        if not valid:
            return f"CON {error_msg}\nEnter amount in sats:"
        
        # Generate invoice
        success, message, invoice_data = ussd_handlers.receive_btc(session.phone_number, amount)
        
        clear_session(session.session_id)
        
        if success:
            return f"END {message}"
        else:
            return f"END Invoice creation failed: {message}"
            
    except ValueError:
        return "CON Invalid amount. Enter amount in sats:"

def handle_send_invoice_phone(session: USSDSession, phone_input: str) -> str:
    """Handle phone number input for sending invoice"""
    if phone_input.lower() == 'back':
        session.set_state("main_menu")
        return handle_main_menu(session)
        
    normalized_phone = ussd_handlers.normalize_phone_number(phone_input)
    
    if not ussd_handlers.validate_phone_number(normalized_phone):
        return "CON Invalid phone number format.\nEnter recipient phone number:"
    
    session.set_data("invoice_recipient", normalized_phone)
    session.set_state("send_invoice_amount")
    return f"CON Send invoice to {normalized_phone}\nEnter amount in sats:"

def handle_send_invoice_amount(session: USSDSession, amount_input: str) -> str:
    """Handle amount input for sending invoice"""
    try:
        if amount_input.lower() == 'back':
            session.set_state("send_invoice_phone")
            return "CON Send Invoice\nEnter recipient phone number:"
            
        amount = int(amount_input)
        recipient_phone = session.get_data("invoice_recipient")
        
        # Validate amount
        valid, error_msg = ussd_handlers.validate_amount(amount)
        if not valid:
            return f"CON {error_msg}\nEnter amount in sats:"
        
        # Send invoice
        success, message, invoice_data = ussd_handlers.send_invoice(session.phone_number, recipient_phone, amount)
        
        clear_session(session.session_id)
        
        if success:
            return f"END {message}"
        else:
            return f"END Invoice sending failed: {message}"
            
    except ValueError:
        return "CON Invalid amount. Enter amount in sats:"

def handle_topup_amount(session: USSDSession, amount_input: str) -> str:
    """Handle amount input for M-Pesa top-up with STK Push"""
    try:
        if amount_input.lower() == 'back':
            session.set_state("main_menu")
            return handle_main_menu(session)
        elif amount_input.lower() in ['rates?', 'rates']:
            return "END Current rate: 1 KES ≈ 6.67 sats\n150 KES = 1,000 sats"
            
        logger.info(f"TOPUP AMOUNT - Raw input: '{amount_input}'")
        logger.info(f"TOPUP AMOUNT - Input bytes: {repr(amount_input)}")
        logger.info(f"TOPUP AMOUNT - Input length: {len(amount_input)}")
        
        # Clean the input - remove whitespace, non-numeric characters
        cleaned_input = ''.join(filter(str.isdigit, amount_input.strip()))
        logger.info(f"TOPUP AMOUNT - Cleaned input: '{cleaned_input}'")
        
        if not cleaned_input:
            logger.warning(f"TOPUP AMOUNT - No digits found in input: '{amount_input}'")
            return ("CON Invalid amount. Please enter a valid number.\n"
                   "Enter KES amount (Min: 10 KES):\n\n"
                   "(Ask 'rates?' or say 'back')")
        
        kes_amount = int(cleaned_input)
        logger.info(f"TOPUP AMOUNT - Parsed KES amount: {kes_amount}")
        
        if kes_amount < 10:
            return ("CON Minimum top-up is 10 KES.\n"
                   "Enter KES amount (Min: 10 KES):\n\n"
                   "(Ask 'rates?' or say 'back')")
        
        sats_equivalent = int(kes_amount * (1000 / 150))
        
        # Directly initiate M-Pesa STK Push with timeout handling
        logger.info(f"TOPUP AMOUNT - Initiating M-Pesa STK Push for {session.phone_number}, amount: {kes_amount} KES ({sats_equivalent} sats)")
        
        try:
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("M-Pesa API timeout")
            
            # Set 15-second timeout for M-Pesa API call
            logger.info(f"TOPUP AMOUNT - Initiating M-Pesa STK Push")
            logger.info(f"TOPUP AMOUNT - Phone: {session.phone_number}")
            logger.info(f"TOPUP AMOUNT - Amount: {kes_amount} KES ({sats_equivalent} sats)")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(15)
            
            success, message, topup_data = ussd_handlers.topup_via_mpesa(session.phone_number, kes_amount)
            
            signal.alarm(0)  # Cancel the alarm
            
            logger.info(f"TOPUP AMOUNT - STK Push result: success={success}")
            logger.info(f"TOPUP AMOUNT - Message: '{message}'")
            logger.info(f"TOPUP AMOUNT - Data: {topup_data}")
            
        except TimeoutError:
            logger.error(f"TOPUP AMOUNT - M-Pesa API timeout for {session.phone_number}")
            clear_session(session.session_id)
            return ("END M-Pesa service temporarily unavailable.\n"
                   f"Please try again or send {kes_amount} KES to PayBill 123456\n"
                   f"Account: {session.phone_number[-9:]}")
        except Exception as e:
            logger.error(f"TOPUP AMOUNT - M-Pesa API error: {e}")
            clear_session(session.session_id)
            return "END Payment service error. Please try again."
        
        clear_session(session.session_id)
        
        if success:
            return f"END {message}"
        else:
            return f"END {message}"
        
    except ValueError as e:
        logger.error(f"TOPUP AMOUNT - ValueError: {e}")
        return ("CON Invalid amount. Please enter a valid number.\n"
               "Enter KES amount (Min: 10 KES):\n\n"
               "(Ask 'rates?' or say 'back')")

def handle_withdraw_amount(session: USSDSession, amount_input: str) -> str:
    """Handle amount input for M-Pesa withdrawal"""
    try:
        if amount_input.lower() == 'back':
            session.set_state("main_menu")
            return handle_main_menu(session)
            
        kes_amount = int(amount_input)
        
        if kes_amount < 100:
            return "CON Minimum withdrawal is 100 KES.\nEnter amount in KES:"
        
        sats_equivalent = int(kes_amount * (1000 / 150))
        current_balance = ussd_handlers.get_user_balance(session.phone_number)
        
        if current_balance < sats_equivalent:
            return f"CON Insufficient balance.\nNeed {sats_equivalent} sats, have {current_balance} sats.\nEnter amount in KES:"
        
        session.set_data("withdraw_kes", kes_amount)
        session.set_state("withdraw_phone")
        
        return f"CON Withdraw {kes_amount} KES ({sats_equivalent} sats)\nEnter M-Pesa phone number:"
        
    except ValueError:
        return "CON Invalid amount. Enter amount in KES:"

def handle_withdraw_phone(session: USSDSession, phone_input: str) -> str:
    """Handle phone number input for M-Pesa withdrawal"""
    if phone_input.lower() == 'back':
        session.set_state("withdraw_amount")
        return "CON Withdraw to M-Pesa\nEnter amount in KES:"
        
    normalized_phone = ussd_handlers.normalize_phone_number(phone_input)
    kes_amount = session.get_data("withdraw_kes")
    
    if not ussd_handlers.validate_phone_number(normalized_phone):
        return "CON Invalid phone number format.\nEnter M-Pesa phone number:"
    
    # Execute withdrawal
    success, message, withdraw_data = ussd_handlers.withdraw_to_mpesa(session.phone_number, kes_amount, normalized_phone)
    
    clear_session(session.session_id)
    
    if success:
        return f"END {message}"
    else:
        return f"END Withdrawal failed: {message}"

def handle_airtime_amount(session: USSDSession, amount_input: str) -> str:
    """Handle amount input for airtime purchase"""
    try:
        if amount_input.lower() == 'back':
            session.set_state("main_menu")
            return handle_main_menu(session)
            
        kes_amount = int(amount_input)
        
        if kes_amount < 10:
            return "CON Minimum airtime purchase is 10 KES.\nEnter amount in KES:"
        
        if kes_amount > 1000:
            return "CON Maximum airtime purchase is 1,000 KES.\nEnter amount in KES:"
        
        session.set_data("airtime_kes", kes_amount)
        session.set_state("airtime_phone")
        
        return f"CON Buy {kes_amount} KES airtime\n\n1. For my number ({session.phone_number})\n2. For another number"
        
    except ValueError:
        return "CON Invalid amount. Enter amount in KES:"

def handle_airtime_phone(session: USSDSession, phone_input: str) -> str:
    """Handle phone number selection for airtime purchase"""
    kes_amount = session.get_data("airtime_kes")
    
    if phone_input.lower() == 'back':
        session.set_state("airtime_amount")
        return "CON Buy Airtime\nEnter amount in KES (10-1000):"
    
    if phone_input == "1":
        # Buy airtime for own number
        airtime_phone = session.phone_number
    elif phone_input == "2":
        return "CON Enter phone number for airtime:"
    else:
        # User entered a phone number directly
        airtime_phone = ussd_handlers.normalize_phone_number(phone_input)
        
        if not ussd_handlers.validate_phone_number(airtime_phone):
            return "CON Invalid phone number format.\nEnter phone number for airtime:"
    
    # Execute airtime purchase
    success, message, airtime_data = ussd_handlers.buy_airtime(session.phone_number, airtime_phone, kes_amount)
    
    clear_session(session.session_id)
    
    if success:
        return f"END {message}"
    else:
        return f"END Airtime purchase failed: {message}"

@app.route('/status', methods=['GET'])
def status():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "service": "Bitcoin Lightning USSD",
        "active_sessions": len(user_sessions)
    })

@app.route('/test', methods=['GET'])
def test():
    """Test endpoint for debugging"""
    test_phone = "+254715586044"  # Your number
    balance = ussd_handlers.get_user_balance(test_phone)
    
    return jsonify({
        "test_phone": test_phone,
        "balance": balance,
        "lightning_api_type": lightning_api.api_type,
        "metta_loaded": True
    })

@app.route('/')
def landing_page():
    """Serve the landing page"""
    try:
        with open('/var/www/btc.emmanuelhaggai.com/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except FileNotFoundError:
        return "Landing page not found", 404

@app.route('/styles.css')
def serve_css():
    """Serve CSS file"""
    try:
        return send_file('/var/www/btc.emmanuelhaggai.com/styles.css', mimetype='text/css')
    except FileNotFoundError:
        return "CSS not found", 404

@app.route('/script.js')
def serve_js():
    """Serve JavaScript file"""
    try:
        return send_file('/var/www/btc.emmanuelhaggai.com/script.js', mimetype='application/javascript')
    except FileNotFoundError:
        return "JS not found", 404

if __name__ == '__main__':
    logger.info("Starting Bitcoin Lightning USSD service...")
    print("STARTUP: Bitcoin Lightning USSD service starting...")
    
    # Initialize balance for your number
    your_phone = "+254715586044"
    lightning_api.set_balance(your_phone, 0)
    ussd_handlers.update_balance(your_phone, 0)
    
    logger.info("Live user balance initialized")
    print("STARTUP: Live user balance initialized")
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)