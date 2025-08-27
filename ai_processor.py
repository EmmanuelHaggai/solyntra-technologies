"""
OpenAI Function Calling Integration for USSD Natural Language Processing
Processes natural language inputs and converts them to USSD actions
"""
import openai
import json
import logging
from typing import Dict, Any, Optional, Tuple
from config import Config
import re

logger = logging.getLogger(__name__)

class USSDNaturalLanguageProcessor:
    """Process natural language USSD inputs using OpenAI function calling"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        
        # Session-based conversation history storage
        # Format: {session_id: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        self.conversation_history = {}
        self.session_context = {}  # Store current operation context per session
        
        # Define available USSD functions
        self.ussd_functions = [
            {
                "type": "function",
                "function": {
                    "name": "send_bitcoin",
                    "description": "Send Bitcoin to another user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {
                                "type": "string",
                                "description": "Recipient phone number or name (e.g., +254712345678, Bob, Alice)"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Amount in satoshis or KES (will be converted)"
                            },
                            "currency": {
                                "type": "string",
                                "enum": ["sats", "satoshis", "KES", "shillings"],
                                "description": "Currency unit"
                            }
                        },
                        "required": ["recipient", "amount", "currency"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_balance",
                    "description": "Check user's Bitcoin balance",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "topup_mpesa",
                    "description": "Top up Bitcoin wallet using M-Pesa",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "Amount in KES"
                            }
                        },
                        "required": ["amount"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "withdraw_mpesa",
                    "description": "Withdraw Bitcoin to M-Pesa",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "Amount in KES or sats"
                            },
                            "currency": {
                                "type": "string",
                                "enum": ["KES", "sats", "satoshis"],
                                "description": "Currency unit"
                            }
                        },
                        "required": ["amount", "currency"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_invoice",
                    "description": "Generate Lightning invoice for receiving Bitcoin",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "Amount in satoshis"
                            },
                            "description": {
                                "type": "string",
                                "description": "Invoice description"
                            }
                        },
                        "required": ["amount"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "show_menu",
                    "description": "Show main USSD menu options",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "transaction_history",
                    "description": "Show recent transaction history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "number",
                                "description": "Number of transactions to show",
                                "default": 5
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "help",
                    "description": "Show help information or explain features",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Specific help topic"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "buy_airtime",
                    "description": "Buy airtime using Bitcoin for Kenyan mobile networks (Safaricom, Airtel, Telkom)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string",
                                "description": "Phone number to top up with airtime (can be own number or another number)"
                            },
                            "amount": {
                                "type": "number",
                                "description": "Amount in KES for airtime purchase (minimum 10 KES, maximum 1000 KES)"
                            }
                        },
                        "required": ["amount"]
                    }
                }
            }
        ]
    
    def add_to_conversation_history(self, session_id: str, role: str, content: str):
        """Add message to conversation history for a session"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "role": role,
            "content": content
        })
        
        # Keep only last 10 messages to avoid token limits
        if len(self.conversation_history[session_id]) > 10:
            self.conversation_history[session_id] = self.conversation_history[session_id][-10:]
    
    def get_conversation_history(self, session_id: str) -> list:
        """Get conversation history for a session"""
        return self.conversation_history.get(session_id, [])
    
    def set_session_context(self, session_id: str, context: Dict[str, Any]):
        """Set context for a session (current operation, expected input, etc.)"""
        self.session_context[session_id] = context
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get context for a session"""
        return self.session_context.get(session_id, {})
    
    def clear_session_context(self, session_id: str):
        """Clear context for a session"""
        if session_id in self.session_context:
            del self.session_context[session_id]
    
    def process_natural_language(self, user_input: str, phone_number: str, 
                               current_balance: int = 0, session_id: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        Process natural language input and determine appropriate action
        
        Returns:
            Tuple of (action_type, action_parameters)
        """
        try:
            # Add user input to conversation history
            if session_id:
                self.add_to_conversation_history(session_id, "user", user_input)
            
            # Get conversation history and session context
            conversation_history = self.get_conversation_history(session_id) if session_id else []
            session_context = self.get_session_context(session_id) if session_id else {}
            
            # Build context-aware system message
            system_message = f"""You are a Bitcoin Lightning Network USSD wallet assistant for Kenya.
            User phone: {phone_number}
            Current balance: {current_balance} sats (≈{current_balance/150:.2f} KES)
            
            CONVERSATION CONTEXT:
            {f"Current operation: {session_context.get('operation', 'None')}" if session_context else ""}
            {f"Awaiting: {session_context.get('awaiting', 'None')}" if session_context else ""}
            {f"Partial data: {session_context.get('data', {})}" if session_context else ""}
            
            Parse user requests and call appropriate functions. Handle various ways users might express their intent:
            
            Examples:
            - "one" or "1" → show_menu or send_bitcoin
            - "what's my balance" → check_balance  
            - "send 5000 to Bob" → send_bitcoin
            - "topup 500" or "buy btc 500 kes" → topup_mpesa (buying Bitcoin with M-Pesa)
            - "withdraw 200 shillings" → withdraw_mpesa
            - "generate invoice 3000" → generate_invoice
            - "buy airtime 100" → buy_airtime
            - "airtime for 50 KES" → buy_airtime
            - "help" → help
            - "history" → transaction_history
            
            IMPORTANT: When users say "buy btc with mpesa", "buy bitcoin", or "topup" - they want to add money TO their wallet.
            Balance doesn't matter for topup operations - users can topup even with 0 balance.
            
            Convert names to phone numbers:
            - Alice: +254712345678
            - Bob: +254787654321  
            - Charlie: +254798765432
            
            Exchange rate: 150 KES = 1000 sats
            
            IMPORTANT: Use conversation history to understand follow-up responses.
            If user previously asked to "top up" and now provides "500", treat as "topup 500 KES".
            If user asked to "send bitcoin" and now provides a phone number, continue the send flow.
            """
            
            # Build messages with conversation history
            messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history (excluding current user input as it's added separately)
            if conversation_history:
                # Don't include the last message since it's the current user input we just added
                messages.extend(conversation_history[:-1])
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.ussd_functions,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Check if AI wants to call a function
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"AI parsed '{user_input}' → {function_name}({function_args})")
                
                # Add assistant response to conversation history
                if session_id:
                    self.add_to_conversation_history(session_id, "assistant", f"Function call: {function_name}({function_args})")
                
                return function_name, function_args
            
            # If no function call, treat as general query
            if session_id:
                self.add_to_conversation_history(session_id, "assistant", message.content)
            
            return "general_response", {"message": message.content}
            
        except Exception as e:
            logger.error(f"Error processing natural language: {e}")
            return "error", {"message": "Sorry, I couldn't understand that. Please try again or use the menu."}
    
    def convert_amount(self, amount: float, from_currency: str, to_currency: str) -> int:
        """Convert between KES and satoshis"""
        # Exchange rate: 150 KES = 1000 sats
        if from_currency.lower() in ["kes", "shillings"] and to_currency.lower() in ["sats", "satoshis"]:
            return int(amount * (1000 / 150))
        elif from_currency.lower() in ["sats", "satoshis"] and to_currency.lower() in ["kes", "shillings"]:
            return int(amount * (150 / 1000))
        else:
            return int(amount)
    
    def resolve_recipient(self, recipient: str) -> str:
        """Convert names to phone numbers"""
        name_to_phone = {
            "alice": "+254712345678",
            "bob": "+254787654321", 
            "charlie": "+254798765432"
        }
        
        recipient_lower = recipient.lower()
        if recipient_lower in name_to_phone:
            return name_to_phone[recipient_lower]
        
        # If it looks like a phone number, return as is
        if recipient.startswith('+254') or recipient.startswith('254') or recipient.startswith('0'):
            return recipient
        
        return recipient
    
    def generate_natural_response(self, action_result: str, context: Dict[str, Any]) -> str:
        """Generate natural language response for action results"""
        try:
            system_message = """You are a helpful Bitcoin Lightning wallet assistant. 
            Convert technical responses into friendly, conversational USSD responses.
            Keep responses concise for mobile display.
            Use emojis sparingly and appropriately for Kenyan users."""
            
            user_message = f"Convert this technical result to a friendly USSD message: {action_result}"
            if context:
                user_message += f" Context: {context}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating natural response: {e}")
            return action_result  # Fallback to original

# Enhanced USSD handler with AI integration
class AIEnhancedUSSDHandler:
    """USSD handler enhanced with OpenAI natural language processing"""
    
    def __init__(self, original_handler):
        self.original_handler = original_handler
        self.ai_processor = USSDNaturalLanguageProcessor()
    
    def should_use_ai(self, user_input: str, session_id: str = None) -> bool:
        """Determine if input should be processed with AI"""
        # Use AI for natural language inputs
        if not user_input or user_input.strip() == "":
            return False
        
        # If there's an active AI session context, always use AI (even for simple inputs like "1")
        if session_id and session_id in self.ai_processor.session_context:
            return True
            
        # Skip AI for simple menu navigation (single digits)
        if user_input.strip() in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            return False
            
        # Use AI for everything else (text, words, complex inputs)
        return True
    
    def process_with_ai(self, user_input: str, phone_number: str, session_id: str) -> str:
        """Process user input with AI and execute appropriate action"""
        try:
            # Get current balance for context
            current_balance = self.original_handler.get_user_balance(phone_number)
            
            # Check if this is a follow-up response to a previous AI request
            session_context = self.ai_processor.get_session_context(session_id)
            if session_context and session_context.get('awaiting'):
                # Extract just the latest input part for context-based responses
                input_parts = user_input.split('*')
                latest_input = input_parts[-1] if input_parts else user_input
                logger.info(f"Processing context-based follow-up: '{latest_input}' in context: {session_context}")
                return self._handle_context_based_response(session_id, phone_number, latest_input, session_context)
            
            # Process with AI including session context
            action_type, action_params = self.ai_processor.process_natural_language(
                user_input, phone_number, current_balance, session_id
            )
            
            logger.info(f"AI determined action: {action_type} with params: {action_params}")
            
            # Execute the determined action
            if action_type == "send_bitcoin":
                return self._handle_ai_send_bitcoin(session_id, phone_number, action_params)
            
            elif action_type == "check_balance":
                return self._handle_ai_check_balance(phone_number)
            
            elif action_type == "topup_mpesa":
                return self._handle_ai_topup_mpesa(session_id, phone_number, action_params)
            
            elif action_type == "withdraw_mpesa":
                return self._handle_ai_withdraw_mpesa(session_id, phone_number, action_params)
            
            elif action_type == "generate_invoice":
                return self._handle_ai_generate_invoice(phone_number, action_params)
            
            elif action_type == "show_menu":
                return self._handle_ai_show_menu(phone_number)
            
            elif action_type == "transaction_history":
                return self._handle_ai_transaction_history(phone_number, action_params)
            
            elif action_type == "help":
                return self._handle_ai_help(action_params)
            
            elif action_type == "buy_airtime":
                return self._handle_ai_buy_airtime(session_id, phone_number, action_params)
            
            elif action_type == "general_response":
                message = action_params.get('message', 'How can I help you?')
                # Check if the message contains a question or request for more info
                if any(word in message.lower() for word in ['amount', 'specify', 'provide', 'enter', 'how much', '?']):
                    return f"CON {message}"
                else:
                    return f"END {message}"
            
            else:
                return "END I didn't understand that. Reply with 'menu' to see options."
                
        except Exception as e:
            logger.error(f"Error in AI processing: {e}")
            return "END Sorry, there was an error. Please try again or use the menu."
    
    def _is_informational_request(self, user_input: str) -> bool:
        """Check if user input is an informational request that should preserve context"""
        informational_keywords = [
            'exchange', 'rate', 'how much', 'what is', 'tell me', 'explain',
            'help', 'info', 'about', 'fees', 'cost', 'price', 'continue',
            'resume', 'back', 'proceed', 'carry on'
        ]
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in informational_keywords)
    
    def _handle_informational_request_with_context(self, session_id: str, phone_number: str, user_input: str, context: Dict) -> str:
        """Handle informational requests while preserving operation context"""
        try:
            operation = context.get('operation')
            awaiting = context.get('awaiting')
            data = context.get('data', {})
            
            # Handle specific informational requests
            user_lower = user_input.lower()
            
            if any(word in user_lower for word in ['exchange', 'rate', 'how much']):
                info_response = "CON Current Exchange Rate:\\n150 KES = 1,000 sats\\n\\n"
                
                if operation == 'topup_mpesa' and awaiting == 'amount':
                    info_response += "You were entering Lightning purchase amount.\\nEnter amount in KES:"
                elif operation == 'withdraw_mpesa' and awaiting == 'amount':
                    info_response += "You were entering withdrawal amount.\\nEnter amount in KES:"
                elif operation == 'send_bitcoin' and awaiting == 'amount':
                    info_response += "You were entering Bitcoin amount.\\nEnter amount in sats:"
                elif operation == 'send_bitcoin' and awaiting == 'recipient':
                    info_response += "You were entering recipient phone.\\nEnter phone number:"
                else:
                    info_response += "Press 0 for main menu."
                    
                return info_response
            
            elif any(word in user_lower for word in ['continue', 'resume', 'proceed', 'carry on', 'back']):
                # Resume the operation where it left off
                if operation == 'topup_mpesa' and awaiting == 'amount':
                    return "CON Lightning Network Purchase\\n\\nBuy Bitcoin via M-Pesa\\nEnter amount in KES:"
                elif operation == 'withdraw_mpesa' and awaiting == 'amount':
                    return "CON M-Pesa Withdrawal\\n\\nEnter amount in KES:"
                elif operation == 'send_bitcoin' and awaiting == 'amount':
                    return "CON Send Bitcoin\\n\\nEnter amount in sats:"
                elif operation == 'send_bitcoin' and awaiting == 'recipient':
                    return "CON Send Bitcoin\\n\\nEnter recipient phone number:"
                else:
                    return "CON No pending operation to continue.\\n\\n0. Main menu"
            
            elif 'help' in user_lower:
                help_response = "CON Lightning Network Help:\\n• 150 KES = 1,000 sats\\n• Min Lightning purchase: 10 KES (66 sats)\\n• Min withdrawal: 100 KES\\n\\n"
                
                if operation and awaiting:
                    help_response += f"Currently: {operation.replace('_', ' ')} - {awaiting}\\n\\n"
                    if awaiting == 'amount':
                        help_response += "Enter numeric amount:"
                    elif awaiting == 'recipient' or awaiting == 'phone_number':
                        help_response += "Enter phone number:"
                else:
                    help_response += "0. Main menu"
                    
                return help_response
            
            else:
                # Generic informational response
                return "CON I can help with exchange rates, fees, and instructions.\\n\\nType 'continue' to resume your transaction or '0' for main menu."
                
        except Exception as e:
            logger.error(f"Error handling informational request: {e}")
            return "CON Type 'continue' to resume or '0' for main menu."
    
    def _handle_context_based_response(self, session_id: str, phone_number: str, user_input: str, context: Dict) -> str:
        """Handle follow-up responses based on session context"""
        try:
            operation = context.get('operation')
            awaiting = context.get('awaiting')
            data = context.get('data', {})
            
            logger.info(f"Handling context-based response: operation={operation}, awaiting={awaiting}, input={user_input}")
            
            # Check if this is an informational request that should preserve context
            if self._is_informational_request(user_input):
                return self._handle_informational_request_with_context(session_id, phone_number, user_input, context)
            
            if operation == 'topup_mpesa':
                if awaiting == 'amount':
                    # User provided amount
                    try:
                        kes_amount = int(user_input.strip())
                        if kes_amount < 10:
                            return "CON Minimum Lightning Network purchase is 10 KES (66 sats).\nEnter amount in KES:"
                        
                        sats_equivalent = int(kes_amount * (1000 / 150))
                        
                        # Update context to await confirmation
                        self.ai_processor.set_session_context(session_id, {
                            'operation': 'topup_mpesa',
                            'awaiting': 'confirmation',
                            'data': {'kes_amount': kes_amount, 'sats_equivalent': sats_equivalent}
                        })
                        
                        return f"CON Top up {kes_amount} KES ({sats_equivalent:,} sats)?\n\n1. Yes, send M-Pesa request\n2. Cancel"
                    except ValueError:
                        return "CON Invalid amount. Enter amount in KES:"
                
                elif awaiting == 'confirmation':
                    # User confirmed the top-up amount
                    if user_input.strip().lower() in ['1', 'yes', 'y', 'confirm']:
                        kes_amount = data.get('kes_amount')
                        # Execute STK push directly (no code needed)
                        success, message, transaction_data = self.original_handler.topup_via_mpesa(phone_number, kes_amount)
                        
                        # Clear context
                        self.ai_processor.clear_session_context(session_id)
                        
                        return f"END {message}"
                    elif user_input.strip().lower() in ['2', 'no', 'n', 'cancel']:
                        self.ai_processor.clear_session_context(session_id)
                        return "END M-Pesa top-up cancelled."
                    else:
                        kes_amount = data.get('kes_amount')
                        sats_equivalent = data.get('sats_equivalent')
                        return f"CON Top up {kes_amount} KES ({sats_equivalent:,} sats)?\n\n1. Yes, send M-Pesa request\n2. Cancel"
            
            elif operation == 'withdraw_mpesa':
                if awaiting == 'amount':
                    # User provided amount
                    try:
                        kes_amount = int(user_input.strip())
                        if kes_amount < 100:
                            return "CON Minimum withdrawal is 100 KES.\nEnter amount in KES:"
                        
                        sats_needed = int(kes_amount * (1000 / 150))
                        
                        # Check balance
                        balance = self.original_handler.get_user_balance(phone_number)
                        if balance < sats_needed:
                            return f"CON Insufficient balance. You have {balance:,} sats, need {sats_needed:,} sats.\nEnter amount in KES:"
                        
                        # Update context to await phone number
                        self.ai_processor.set_session_context(session_id, {
                            'operation': 'withdraw_mpesa',
                            'awaiting': 'phone_number',
                            'data': {'kes_amount': kes_amount, 'sats_needed': sats_needed}
                        })
                        
                        return f"CON Withdraw {kes_amount} KES ({sats_needed:,} sats)\nEnter M-Pesa phone number:"
                    except ValueError:
                        return "CON Invalid amount. Enter amount in KES:"
                
                elif awaiting == 'phone_number':
                    # User provided phone number
                    phone_input = user_input.strip()
                    normalized_phone = self.original_handler.normalize_phone_number(phone_input)
                    
                    if not self.original_handler.validate_phone_number(normalized_phone):
                        return "CON Invalid phone number format.\nEnter M-Pesa phone number:"
                    
                    kes_amount = data.get('kes_amount')
                    # Execute withdrawal
                    success, message, _ = self.original_handler.withdraw_to_mpesa(phone_number, kes_amount, normalized_phone)
                    
                    # Clear context
                    self.ai_processor.clear_session_context(session_id)
                    
                    return f"END {message}"
            
            elif operation == 'buy_airtime':
                if awaiting == 'amount':
                    # User provided amount
                    try:
                        kes_amount = int(user_input.strip())
                        if kes_amount < 10:
                            return "CON Minimum airtime purchase is 10 KES.\nEnter amount in KES:"
                        if kes_amount > 1000:
                            return "CON Maximum airtime purchase is 1,000 KES.\nEnter amount in KES:"
                        
                        # Ask if they want to buy for themselves or another number
                        self.ai_processor.set_session_context(session_id, {
                            'operation': 'buy_airtime',
                            'awaiting': 'phone_confirmation',
                            'data': {'kes_amount': kes_amount}
                        })
                        return f"CON Buy {kes_amount} KES airtime\n\n1. For my number ({phone_number})\n2. For another number"
                    except ValueError:
                        return "CON Invalid amount. Enter amount in KES:"
                
                elif awaiting == 'phone_confirmation':
                    # User chose 1 or 2
                    kes_amount = data.get('kes_amount')
                    if user_input.strip() == '1':
                        # Buy for own number
                        success, message, airtime_data = self.original_handler.buy_airtime(
                            phone_number, phone_number, kes_amount
                        )
                        self.ai_processor.clear_session_context(session_id)
                        return f"END {message}"
                    elif user_input.strip() == '2':
                        # Ask for another number
                        self.ai_processor.set_session_context(session_id, {
                            'operation': 'buy_airtime',
                            'awaiting': 'phone_number',
                            'data': {'kes_amount': kes_amount}
                        })
                        return "CON Enter phone number for airtime:"
                    else:
                        return f"CON Buy {kes_amount} KES airtime\n\n1. For my number ({phone_number})\n2. For another number"
                
                elif awaiting == 'phone_number':
                    # User provided phone number
                    phone_input = user_input.strip()
                    normalized_phone = self.original_handler.normalize_phone_number(phone_input)
                    
                    if not self.original_handler.validate_phone_number(normalized_phone):
                        return "CON Invalid phone number format.\nEnter phone number for airtime:"
                    
                    kes_amount = data.get('kes_amount')
                    # Execute airtime purchase
                    success, message, airtime_data = self.original_handler.buy_airtime(
                        phone_number, normalized_phone, kes_amount
                    )
                    
                    # Clear context
                    self.ai_processor.clear_session_context(session_id)
                    
                    return f"END {message}"
            
            # If we don't handle this context, clear it and process normally
            self.ai_processor.clear_session_context(session_id)
            return "END I didn't understand your response. Please try again or say 'menu' for options."
            
        except Exception as e:
            logger.error(f"Error in context-based response: {e}")
            self.ai_processor.clear_session_context(session_id)
            return "END Error processing your response. Please try again."
    
    def _handle_ai_send_bitcoin(self, session_id: str, phone_number: str, params: Dict) -> str:
        """Handle AI-determined send bitcoin request"""
        try:
            # Check if we have both recipient and amount
            if 'recipient' not in params or 'amount' not in params:
                return "CON Send BTC\nEnter recipient phone number:"
            
            recipient = self.ai_processor.resolve_recipient(params['recipient'])
            amount = params['amount']
            currency = params.get('currency', 'sats')
            
            # Convert to sats if necessary
            if currency.lower() in ['kes', 'shillings']:
                amount_sats = self.ai_processor.convert_amount(amount, currency, 'sats')
            else:
                amount_sats = int(amount)
            
            # Validate amount (Lightning Network can handle small amounts)
            if amount_sats < 10:
                return "CON Minimum send amount is 10 sats (≈0.015 KES)\nEnter amount in sats:"
            
            if amount_sats > 1000000:
                return "CON Maximum send amount is 1,000,000 sats (≈6,667 KES)\nEnter amount in sats:"
            
            # Check balance
            balance = self.original_handler.get_user_balance(phone_number)
            if balance < amount_sats:
                return f"CON Insufficient balance. You have {balance:,} sats, need {amount_sats:,} sats.\nEnter amount in sats:"
            
            # Execute the send
            success, message, _ = self.original_handler.send_btc(
                phone_number, recipient, amount_sats
            )
            
            if success:
                # Generate natural language response
                natural_response = self.ai_processor.generate_natural_response(
                    f"Successfully sent {amount_sats} sats to {recipient}",
                    {"original_amount": amount, "currency": currency}
                )
                return f"END {natural_response}"
            else:
                return f"END Send failed: {message}"
                
        except Exception as e:
            logger.error(f"AI send bitcoin error: {e}")
            return "CON Send BTC\nEnter recipient phone number:"
    
    def _handle_ai_check_balance(self, phone_number: str) -> str:
        """Handle AI balance check request"""
        try:
            balance = self.original_handler.get_user_balance(phone_number)
            balance_kes = balance * 150 / 1000
            
            natural_response = self.ai_processor.generate_natural_response(
                f"Your balance is {balance:,} sats (≈{balance_kes:.2f} KES)",
                {"sats": balance, "kes": balance_kes}
            )
            return f"END {natural_response}"
            
        except Exception as e:
            logger.error(f"AI balance check error: {e}")
            return "END Error checking balance. Please try again."
    
    def _handle_ai_topup_mpesa(self, session_id: str, phone_number: str, params: Dict) -> str:
        """Handle AI M-Pesa topup request"""
        try:
            # If amount is provided, go directly to asking for M-Pesa code
            if 'amount' in params and params['amount']:
                kes_amount = int(params['amount'])
                
                if kes_amount < 10:
                    # Set context for amount collection
                    self.ai_processor.set_session_context(session_id, {
                        'operation': 'topup_mpesa',
                        'awaiting': 'amount',
                        'data': {}
                    })
                    return "CON Minimum Lightning purchase is 10 KES (66 sats).\nEnter amount in KES:"
                
                sats_equivalent = int(kes_amount * (1000 / 150))
                
                # Set context for confirmation
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'topup_mpesa',
                    'awaiting': 'confirmation',
                    'data': {'kes_amount': kes_amount, 'sats_equivalent': sats_equivalent}
                })
                
                return f"CON Top up {kes_amount} KES ({sats_equivalent:,} sats)?\n\n1. Yes, send M-Pesa request\n2. Cancel"
            else:
                # Ask for amount first
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'topup_mpesa',
                    'awaiting': 'amount',
                    'data': {}
                })
                return "CON Top Up via M-Pesa\nEnter amount in KES:"
            
        except Exception as e:
            logger.error(f"AI topup error: {e}")
            return "CON Top Up via M-Pesa\nEnter amount in KES:"
    
    def _handle_ai_withdraw_mpesa(self, session_id: str, phone_number: str, params: Dict) -> str:
        """Handle AI M-Pesa withdrawal request"""
        try:
            # If amount is provided, ask for M-Pesa phone number
            if 'amount' in params and params['amount']:
                amount = params['amount']
                currency = params.get('currency', 'KES')
                
                if currency.lower() in ['kes', 'shillings']:
                    kes_amount = int(amount)
                    sats_needed = int(kes_amount * (1000 / 150))
                else:
                    sats_needed = int(amount)
                    kes_amount = int(sats_needed * 150 / 1000)
                
                if kes_amount < 100:
                    # Set context for amount collection
                    self.ai_processor.set_session_context(session_id, {
                        'operation': 'withdraw_mpesa',
                        'awaiting': 'amount',
                        'data': {}
                    })
                    return "CON Minimum withdrawal is 100 KES.\nEnter amount in KES:"
                
                # Check balance
                balance = self.original_handler.get_user_balance(phone_number)
                if balance < sats_needed:
                    self.ai_processor.set_session_context(session_id, {
                        'operation': 'withdraw_mpesa',
                        'awaiting': 'amount',
                        'data': {}
                    })
                    return f"CON Insufficient balance. You have {balance:,} sats, need {sats_needed:,} sats.\nEnter amount in KES:"
                
                # Set context for phone number collection
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'withdraw_mpesa',
                    'awaiting': 'phone_number',
                    'data': {'kes_amount': kes_amount, 'sats_needed': sats_needed}
                })
                
                return f"CON Withdraw {kes_amount} KES ({sats_needed:,} sats)\nEnter M-Pesa phone number:"
            else:
                # Ask for amount first
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'withdraw_mpesa',
                    'awaiting': 'amount',
                    'data': {}
                })
                return "CON Withdraw to M-Pesa\nEnter amount in KES:"
                
        except Exception as e:
            logger.error(f"AI withdrawal error: {e}")
            return "CON Withdraw to M-Pesa\nEnter amount in KES:"
    
    def _handle_ai_generate_invoice(self, phone_number: str, params: Dict) -> str:
        """Handle AI invoice generation request"""
        try:
            amount_sats = int(params['amount'])
            description = params.get('description', f"Payment request for {amount_sats} sats")
            
            success, message, invoice_data = self.original_handler.receive_btc(
                phone_number, amount_sats, description
            )
            
            if success:
                return f"END {message}"
            else:
                return f"END Invoice generation failed: {message}"
                
        except Exception as e:
            logger.error(f"AI invoice generation error: {e}")
            return "END Error generating invoice."
    
    def _handle_ai_show_menu(self, phone_number: str) -> str:
        """Show main menu with balance"""
        balance = self.original_handler.get_user_balance(phone_number)
        menu = self.original_handler.get_menu_text("en")
        return f"CON Lightning Wallet\nBalance: {balance:,} sats\n\n{menu}"
    
    def _handle_ai_transaction_history(self, phone_number: str, params: Dict) -> str:
        """Show transaction history"""
        try:
            limit = params.get('limit', 5)
            transactions = self.original_handler.get_transaction_history(phone_number, limit)
            
            if not transactions:
                return "END No recent transactions found."
            
            history_text = "END Recent Transactions:\n\n"
            for tx in transactions:
                tx_type = tx['type']
                amount = tx['amount']
                timestamp = tx['timestamp'][:10]  # Date only
                
                if tx_type == 'Lightning':
                    if tx['from'] == phone_number:
                        history_text += f"Sent {amount:,} sats ({timestamp})\n"
                    else:
                        history_text += f"Received {amount:,} sats ({timestamp})\n"
                else:
                    history_text += f"{tx_type}: {amount:,} sats ({timestamp})\n"
            
            return history_text
            
        except Exception as e:
            logger.error(f"AI transaction history error: {e}")
            return "END Error fetching transaction history."
    
    def _handle_ai_help(self, params: Dict) -> str:
        """Provide help information"""
        topic = params.get('topic', 'general')
        
        help_text = "END Lightning Wallet Help:\n\n"
        help_text += "You can say things like:\n"
        help_text += "• 'Check my balance'\n"
        help_text += "• 'Send 5000 to Bob'\n"
        help_text += "• 'Top up 500 KES'\n"
        help_text += "• 'Buy airtime 100 KES'\n"
        help_text += "• 'Generate invoice 3000'\n"
        help_text += "• 'Show history'\n"
        help_text += "• Or use menu options 1-6"
        
        return help_text
    
    def _handle_ai_buy_airtime(self, session_id: str, phone_number: str, params: Dict) -> str:
        """Handle AI airtime purchase request"""
        try:
            # Check if we have the required amount
            if 'amount' not in params or not params['amount']:
                # Set context for amount collection
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'buy_airtime',
                    'awaiting': 'amount',
                    'data': {}
                })
                return "CON Buy Airtime\nEnter amount in KES (10-1000):"
            
            kes_amount = int(params['amount'])
            
            if kes_amount < 10:
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'buy_airtime',
                    'awaiting': 'amount',
                    'data': {}
                })
                return "CON Minimum airtime purchase is 10 KES.\nEnter amount in KES:"
            
            if kes_amount > 1000:
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'buy_airtime',
                    'awaiting': 'amount',
                    'data': {}
                })
                return "CON Maximum airtime purchase is 1,000 KES.\nEnter amount in KES:"
            
            # Check if phone number is provided, otherwise ask for it
            airtime_phone = params.get('phone_number', phone_number)
            
            if not airtime_phone or airtime_phone == phone_number:
                # Ask if they want to buy for themselves or another number
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'buy_airtime',
                    'awaiting': 'phone_confirmation',
                    'data': {'kes_amount': kes_amount}
                })
                return f"CON Buy {kes_amount} KES airtime\n\n1. For my number ({phone_number})\n2. For another number"
            
            # Validate the phone number
            normalized_phone = self.original_handler.normalize_phone_number(airtime_phone)
            if not self.original_handler.validate_phone_number(normalized_phone):
                self.ai_processor.set_session_context(session_id, {
                    'operation': 'buy_airtime',
                    'awaiting': 'phone_number',
                    'data': {'kes_amount': kes_amount}
                })
                return "CON Invalid phone number.\nEnter phone number for airtime:"
            
            # Execute airtime purchase
            success, message, airtime_data = self.original_handler.buy_airtime(
                phone_number, normalized_phone, kes_amount
            )
            
            # Clear context
            self.ai_processor.clear_session_context(session_id)
            
            if success:
                # Generate natural language response
                natural_response = self.ai_processor.generate_natural_response(
                    message,
                    {"kes_amount": kes_amount, "carrier": airtime_data.get('carrier')}
                )
                return f"END {natural_response}"
            else:
                return f"END Airtime purchase failed: {message}"
                
        except Exception as e:
            logger.error(f"AI airtime purchase error: {e}")
            self.ai_processor.clear_session_context(session_id)
            return "CON Buy Airtime\nEnter amount in KES (10-1000):"

# Global AI processor instance
ai_processor = USSDNaturalLanguageProcessor()