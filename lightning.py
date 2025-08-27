"""
Lightning Network API wrapper supporting LND REST/gRPC and LNbits
"""
import requests
import json
import logging
from typing import Dict, Any, Optional, Tuple
import base64
import time
from database import get_session
from models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LightningAPI:
    def __init__(self, api_type: str = "mock", **config):
        self.api_type = api_type
        self.config = config
        self.mock_data = {
            "users": {},
            "invoices": {},
            "payments": []
        }
    
    def get_balance(self, user_id: str) -> int:
        """Get user balance in satoshis"""
        if self.api_type == "mock":
            return self._get_db_balance(user_id)
        elif self.api_type == "lnbits":
            return self._lnbits_get_balance(user_id)
        elif self.api_type == "lnd":
            return self._lnd_get_balance()
        elif self.api_type == "btcpay":
            return self._btcpay_get_balance(user_id)
        return 0
    
    def create_invoice(self, user_id: str, amount: int, memo: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Create Lightning invoice"""
        if self.api_type == "mock":
            invoice_id = f"inv_{int(time.time())}_{user_id}"
            invoice_data = {
                "payment_request": f"lnbc{amount}1pwxyz...",
                "payment_hash": f"hash_{invoice_id}",
                "amount": amount,
                "memo": memo,
                "user_id": user_id,
                "paid": False,
                "expires_at": int(time.time()) + 3600
            }
            self.mock_data["invoices"][invoice_id] = invoice_data
            return True, {"invoice_id": invoice_id, **invoice_data}
        elif self.api_type == "lnbits":
            return self._lnbits_create_invoice(user_id, amount, memo)
        elif self.api_type == "lnd":
            return self._lnd_create_invoice(amount, memo)
        elif self.api_type == "btcpay":
            return self._btcpay_create_invoice(user_id, amount, memo)
        return False, {"error": "Unsupported API type"}
    
    def pay_invoice(self, user_id: str, payment_request: str) -> Tuple[bool, Dict[str, Any]]:
        """Pay Lightning invoice"""
        if self.api_type == "mock":
            # Find invoice by payment request
            invoice = None
            for inv_id, inv_data in self.mock_data["invoices"].items():
                if inv_data["payment_request"] == payment_request:
                    invoice = inv_data
                    break
            
            if not invoice:
                return False, {"error": "Invoice not found"}
            
            if invoice["paid"]:
                return False, {"error": "Invoice already paid"}
            
            sender_balance = self.get_balance(user_id)
            if sender_balance < invoice["amount"]:
                return False, {"error": "Insufficient balance"}
            
            # Update balances
            self._update_db_balance(user_id, -invoice["amount"])
            self._update_db_balance(invoice["user_id"], invoice["amount"])
            
            # Mark invoice as paid
            invoice["paid"] = True
            
            payment_record = {
                "from": user_id,
                "to": invoice["user_id"],
                "amount": invoice["amount"],
                "timestamp": int(time.time()),
                "payment_hash": invoice["payment_hash"]
            }
            self.mock_data["payments"].append(payment_record)
            
            return True, payment_record
        elif self.api_type == "lnbits":
            return self._lnbits_pay_invoice(user_id, payment_request)
        elif self.api_type == "lnd":
            return self._lnd_pay_invoice(payment_request)
        elif self.api_type == "btcpay":
            return self._btcpay_pay_invoice(user_id, payment_request)
        return False, {"error": "Unsupported API type"}
    
    def check_invoice(self, invoice_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check invoice status"""
        if self.api_type == "mock":
            invoice = self.mock_data["invoices"].get(invoice_id)
            if not invoice:
                return False, {"error": "Invoice not found"}
            return True, invoice
        elif self.api_type == "lnbits":
            return self._lnbits_check_invoice(invoice_id)
        elif self.api_type == "lnd":
            return self._lnd_check_invoice(invoice_id)
        elif self.api_type == "btcpay":
            return self._btcpay_check_invoice(invoice_id)
        return False, {"error": "Unsupported API type"}
    
    def _get_db_balance(self, user_id: str) -> int:
        """Get user balance from database"""
        try:
            with get_session() as session:
                user = session.query(User).filter_by(phone_number=user_id).first()
                if user:
                    return user.balance_sats
                return 0
        except Exception as e:
            logger.error(f"Database balance error: {e}")
            return 0

    def _update_db_balance(self, user_id: str, amount_change: int):
        """Update user balance in database"""
        try:
            with get_session() as session:
                user = session.query(User).filter_by(phone_number=user_id).first()
                if user:
                    user.balance_sats += amount_change
                    if user.balance_sats < 0:
                        user.balance_sats = 0
                else:
                    # Create new user with initial balance
                    user = User(phone_number=user_id, balance_sats=max(0, amount_change))
                    session.add(user)
                session.commit()
        except Exception as e:
            logger.error(f"Database balance update error: {e}")

    def _update_balance(self, user_id: str, amount_change: int):
        """Update user balance (database-backed)"""
        self._update_db_balance(user_id, amount_change)
    
    def set_balance(self, user_id: str, amount: int):
        """Set user balance (database-backed)"""
        if self.api_type == "mock":
            self._set_db_balance(user_id, amount)

    def _set_db_balance(self, user_id: str, amount: int):
        """Set user balance in database"""
        try:
            with get_session() as session:
                user = session.query(User).filter_by(phone_number=user_id).first()
                if user:
                    user.balance_sats = amount
                else:
                    # Create new user with specified balance
                    user = User(phone_number=user_id, balance_sats=amount)
                    session.add(user)
                session.commit()
        except Exception as e:
            logger.error(f"Database balance set error: {e}")
    
    # LNbits API methods
    def _lnbits_get_balance(self, user_id: str) -> int:
        """Get balance from LNbits"""
        try:
            headers = {
                "X-Api-Key": self.config.get("lnbits_admin_key", ""),
                "Content-Type": "application/json"
            }
            wallet_id = self.config.get("wallet_mapping", {}).get(user_id)
            if not wallet_id:
                return 0
                
            response = requests.get(
                f"{self.config['lnbits_url']}/api/v1/wallet",
                headers={**headers, "X-Api-Key": wallet_id}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("balance", 0) // 1000  # Convert from msats
            return 0
        except Exception as e:
            logger.error(f"LNbits balance error: {e}")
            return 0
    
    def _lnbits_create_invoice(self, user_id: str, amount: int, memo: str) -> Tuple[bool, Dict[str, Any]]:
        """Create invoice via LNbits"""
        try:
            headers = {
                "X-Api-Key": self.config.get("lnbits_admin_key", ""),
                "Content-Type": "application/json"
            }
            data = {
                "out": False,
                "amount": amount,
                "memo": memo
            }
            response = requests.post(
                f"{self.config['lnbits_url']}/api/v1/payments",
                headers=headers,
                json=data
            )
            if response.status_code == 201:
                return True, response.json()
            return False, {"error": "Failed to create invoice"}
        except Exception as e:
            logger.error(f"LNbits create invoice error: {e}")
            return False, {"error": str(e)}
    
    def _lnbits_pay_invoice(self, user_id: str, payment_request: str) -> Tuple[bool, Dict[str, Any]]:
        """Pay invoice via LNbits"""
        try:
            headers = {
                "X-Api-Key": self.config.get("lnbits_admin_key", ""),
                "Content-Type": "application/json"
            }
            data = {
                "out": True,
                "bolt11": payment_request
            }
            response = requests.post(
                f"{self.config['lnbits_url']}/api/v1/payments",
                headers=headers,
                json=data
            )
            if response.status_code == 201:
                return True, response.json()
            return False, {"error": "Failed to pay invoice"}
        except Exception as e:
            logger.error(f"LNbits pay invoice error: {e}")
            return False, {"error": str(e)}
    
    def _lnbits_check_invoice(self, invoice_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check invoice status via LNbits"""
        try:
            headers = {
                "X-Api-Key": self.config.get("lnbits_admin_key", ""),
                "Content-Type": "application/json"
            }
            response = requests.get(
                f"{self.config['lnbits_url']}/api/v1/payments/{invoice_id}",
                headers=headers
            )
            if response.status_code == 200:
                return True, response.json()
            return False, {"error": "Invoice not found"}
        except Exception as e:
            logger.error(f"LNbits check invoice error: {e}")
            return False, {"error": str(e)}
    
    # LND API methods (basic implementation)
    def _lnd_get_balance(self) -> int:
        """Get balance from LND"""
        try:
            headers = {
                "Grpc-Metadata-macaroon": self.config.get("lnd_macaroon", "")
            }
            response = requests.get(
                f"{self.config['lnd_url']}/v1/balance/channels",
                headers=headers,
                verify=False if self.config.get("lnd_skip_verify") else True
            )
            if response.status_code == 200:
                data = response.json()
                return int(data.get("balance", "0"))
            return 0
        except Exception as e:
            logger.error(f"LND balance error: {e}")
            return 0
    
    def _lnd_create_invoice(self, amount: int, memo: str) -> Tuple[bool, Dict[str, Any]]:
        """Create invoice via LND"""
        try:
            headers = {
                "Grpc-Metadata-macaroon": self.config.get("lnd_macaroon", ""),
                "Content-Type": "application/json"
            }
            data = {
                "value": str(amount),
                "memo": memo,
                "expiry": "3600"
            }
            response = requests.post(
                f"{self.config['lnd_url']}/v1/invoices",
                headers=headers,
                json=data,
                verify=False if self.config.get("lnd_skip_verify") else True
            )
            if response.status_code == 200:
                return True, response.json()
            return False, {"error": "Failed to create invoice"}
        except Exception as e:
            logger.error(f"LND create invoice error: {e}")
            return False, {"error": str(e)}
    
    def _lnd_pay_invoice(self, payment_request: str) -> Tuple[bool, Dict[str, Any]]:
        """Pay invoice via LND"""
        try:
            headers = {
                "Grpc-Metadata-macaroon": self.config.get("lnd_macaroon", ""),
                "Content-Type": "application/json"
            }
            data = {
                "payment_request": payment_request
            }
            response = requests.post(
                f"{self.config['lnd_url']}/v1/channels/transactions",
                headers=headers,
                json=data,
                verify=False if self.config.get("lnd_skip_verify") else True
            )
            if response.status_code == 200:
                return True, response.json()
            return False, {"error": "Failed to pay invoice"}
        except Exception as e:
            logger.error(f"LND pay invoice error: {e}")
            return False, {"error": str(e)}
    
    def _lnd_check_invoice(self, invoice_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check invoice status via LND"""
        try:
            headers = {
                "Grpc-Metadata-macaroon": self.config.get("lnd_macaroon", "")
            }
            response = requests.get(
                f"{self.config['lnd_url']}/v1/invoice/{invoice_id}",
                headers=headers,
                verify=False if self.config.get("lnd_skip_verify") else True
            )
            if response.status_code == 200:
                return True, response.json()
            return False, {"error": "Invoice not found"}
        except Exception as e:
            logger.error(f"LND check invoice error: {e}")
            return False, {"error": str(e)}
    
    # BTCPay Server API methods
    def _btcpay_get_balance(self, user_id: str) -> int:
        """Get balance from BTCPay Server"""
        try:
            # Note: BTCPay doesn't have user-specific balances like LNbits
            # This would need to be managed at application level
            headers = {
                "Authorization": f"token {self.config.get('btcpay_api_key', '')}",
                "Content-Type": "application/json"
            }
            store_id = self.config.get("btcpay_store_id", "")
            
            # For now, return balance from our own tracking
            # In a real implementation, you might query Lightning Node balance
            return self.mock_data["users"].get(user_id, {}).get("balance", 0)
        except Exception as e:
            logger.error(f"BTCPay balance error: {e}")
            return 0
    
    def _btcpay_create_invoice(self, user_id: str, amount: int, memo: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Create invoice via BTCPay Server"""
        try:
            headers = {
                "Authorization": f"token {self.config.get('btcpay_api_key', '')}",
                "Content-Type": "application/json"
            }
            store_id = self.config.get("btcpay_store_id", "")
            btcpay_url = self.config.get("btcpay_url", "")
            
            # Convert satoshis to BTC for BTCPay
            amount_btc = amount / 100000000
            
            data = {
                "amount": str(amount_btc),
                "currency": "BTC",
                "metadata": {
                    "orderId": f"ussd_{user_id}_{int(time.time())}",
                    "itemDesc": memo or "Lightning payment via USSD"
                },
                "checkout": {
                    "speedPolicy": "HighSpeed",
                    "expirationMinutes": 60,
                    "lightningMaxValue": str(amount_btc),
                    "onChainMinValue": str(amount_btc * 2)  # Prefer Lightning
                }
            }
            
            response = requests.post(
                f"{btcpay_url}/api/v1/stores/{store_id}/invoices",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                invoice_data = response.json()
                return True, {
                    "invoice_id": invoice_data["id"],
                    "payment_request": invoice_data.get("BOLT11", ""),
                    "payment_hash": invoice_data.get("id"),
                    "amount": amount,
                    "memo": memo,
                    "user_id": user_id,
                    "expires_at": int(time.time()) + 3600,
                    "checkout_link": invoice_data.get("checkoutLink", "")
                }
            else:
                logger.error(f"BTCPay invoice creation failed: {response.status_code} {response.text}")
                return False, {"error": f"Failed to create invoice: {response.text}"}
        except Exception as e:
            logger.error(f"BTCPay create invoice error: {e}")
            return False, {"error": str(e)}
    
    def _btcpay_pay_invoice(self, user_id: str, payment_request: str) -> Tuple[bool, Dict[str, Any]]:
        """Pay invoice via BTCPay Server"""
        try:
            # BTCPay Server doesn't have a direct "pay invoice" API
            # This would typically be handled by the Lightning Node itself
            # For now, we'll simulate payment in mock mode
            logger.warning("BTCPay payment simulation - implement with actual Lightning Node")
            return False, {"error": "Payment via BTCPay requires external Lightning wallet"}
        except Exception as e:
            logger.error(f"BTCPay pay invoice error: {e}")
            return False, {"error": str(e)}
    
    def _btcpay_check_invoice(self, invoice_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Check invoice status via BTCPay Server"""
        try:
            headers = {
                "Authorization": f"token {self.config.get('btcpay_api_key', '')}",
                "Content-Type": "application/json"
            }
            store_id = self.config.get("btcpay_store_id", "")
            btcpay_url = self.config.get("btcpay_url", "")
            
            response = requests.get(
                f"{btcpay_url}/api/v1/stores/{store_id}/invoices/{invoice_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                invoice_data = response.json()
                is_paid = invoice_data.get("status") == "Settled"
                
                return True, {
                    "invoice_id": invoice_id,
                    "paid": is_paid,
                    "status": invoice_data.get("status"),
                    "amount": invoice_data.get("amount"),
                    "payment_request": invoice_data.get("BOLT11", ""),
                    "expires_at": invoice_data.get("expirationTime"),
                    "checkout_link": invoice_data.get("checkoutLink", "")
                }
            else:
                logger.error(f"BTCPay invoice check failed: {response.status_code}")
                return False, {"error": "Invoice not found"}
        except Exception as e:
            logger.error(f"BTCPay check invoice error: {e}")
            return False, {"error": str(e)}

# Initialize default Lightning API instance
lightning_api = LightningAPI("mock")