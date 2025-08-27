#!/usr/bin/env python3
"""
BTCPay Server Health Check and Initialization Script
Checks if BTCPay Server is ready and performs initial setup
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, Optional
from config import Config

class BTCPayHealthCheck:
    def __init__(self):
        self.btcpay_url = Config.BTCPAY_URL or "http://localhost:23000"
        self.api_key = Config.BTCPAY_API_KEY
        self.store_id = Config.BTCPAY_STORE_ID
        
    def check_btcpay_server(self) -> bool:
        """Check if BTCPay Server is accessible"""
        try:
            response = requests.get(f"{self.btcpay_url}/health", timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def check_api_access(self) -> bool:
        """Check if API key provides access"""
        if not self.api_key:
            return False
            
        try:
            headers = {
                "Authorization": f"token {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(f"{self.btcpay_url}/api/v1/api-keys/current", headers=headers, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def check_store_access(self) -> bool:
        """Check if store ID is accessible"""
        if not self.api_key or not self.store_id:
            return False
            
        try:
            headers = {
                "Authorization": f"token {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(f"{self.btcpay_url}/api/v1/stores/{self.store_id}", headers=headers, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get BTCPay Server information"""
        try:
            response = requests.get(f"{self.btcpay_url}/api/v1/server/info", timeout=10)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None
    
    def get_store_info(self) -> Optional[Dict[str, Any]]:
        """Get store information"""
        if not self.api_key or not self.store_id:
            return None
            
        try:
            headers = {
                "Authorization": f"token {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(f"{self.btcpay_url}/api/v1/stores/{self.store_id}", headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None
    
    def test_invoice_creation(self) -> bool:
        """Test creating a simple invoice"""
        if not self.api_key or not self.store_id:
            return False
            
        try:
            headers = {
                "Authorization": f"token {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "amount": "0.00001",  # 1000 sats
                "currency": "BTC",
                "metadata": {
                    "orderId": f"health_check_{int(time.time())}",
                    "itemDesc": "Health check test invoice"
                }
            }
            
            response = requests.post(
                f"{self.btcpay_url}/api/v1/stores/{self.store_id}/invoices",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                # Clean up - mark test invoice as invalid
                invoice_data = response.json()
                print(f"✅ Test invoice created: {invoice_data.get('id')}")
                return True
                
        except requests.RequestException:
            pass
        return False
    
    def wait_for_services(self, timeout: int = 300) -> bool:
        """Wait for BTCPay Server and dependencies to be ready"""
        print("⏳ Waiting for BTCPay Server to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_btcpay_server():
                print("✅ BTCPay Server is accessible")
                time.sleep(5)  # Give it a few more seconds
                return True
            print("⏳ Waiting for BTCPay Server... (will retry)")
            time.sleep(10)
        
        print("❌ Timeout waiting for BTCPay Server")
        return False
    
    def run_health_check(self) -> bool:
        """Run complete health check"""
        print("=" * 50)
        print("BTCPay Server Health Check")
        print("=" * 50)
        
        # Check server accessibility
        print(f"🔍 Checking BTCPay Server at {self.btcpay_url}")
        if not self.check_btcpay_server():
            print("❌ BTCPay Server is not accessible")
            return False
        print("✅ BTCPay Server is accessible")
        
        # Get server info
        server_info = self.get_server_info()
        if server_info:
            print(f"📋 Server Version: {server_info.get('version', 'Unknown')}")
        
        # Check API access
        print("🔑 Checking API key access")
        if not self.check_api_access():
            if not self.api_key:
                print("⚠️  No API key configured")
            else:
                print("❌ API key is invalid or insufficient permissions")
            print("💡 Please generate an API key in BTCPay Server with invoice permissions")
            return False
        print("✅ API key is valid")
        
        # Check store access
        print("🏪 Checking store access")
        if not self.check_store_access():
            if not self.store_id:
                print("⚠️  No store ID configured")
            else:
                print("❌ Store ID is invalid or inaccessible")
            print("💡 Please create a store in BTCPay Server and update BTCPAY_STORE_ID")
            return False
        print("✅ Store access confirmed")
        
        # Get store info
        store_info = self.get_store_info()
        if store_info:
            print(f"📋 Store Name: {store_info.get('name', 'Unknown')}")
        
        # Test invoice creation
        print("🧾 Testing invoice creation")
        if not self.test_invoice_creation():
            print("❌ Failed to create test invoice")
            return False
        print("✅ Invoice creation test passed")
        
        print("=" * 50)
        print("🎉 All health checks passed! BTCPay Server is ready.")
        print("=" * 50)
        return True
    
    def show_configuration_help(self):
        """Show help for configuring BTCPay Server"""
        print("=" * 50)
        print("BTCPay Server Configuration Help")
        print("=" * 50)
        print("1. Visit your BTCPay Server: http://localhost:23000")
        print("2. Create an account and store")
        print("3. Go to Store Settings > Access Tokens")
        print("4. Create new API key with these permissions:")
        print("   - btcpay.store.cancreateinvoice")
        print("   - btcpay.store.canviewinvoices")
        print("5. Update your .env file:")
        print(f"   BTCPAY_URL={self.btcpay_url}")
        print("   BTCPAY_API_KEY=your_api_key_here")
        print("   BTCPAY_STORE_ID=your_store_id_here")
        print("6. Re-run this health check")
        print("=" * 50)

def main():
    """Main function"""
    health_checker = BTCPayHealthCheck()
    
    if len(sys.argv) > 1 and sys.argv[1] == "wait":
        # Wait for services mode
        if health_checker.wait_for_services():
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Run health check
    success = health_checker.run_health_check()
    
    if not success:
        health_checker.show_configuration_help()
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()