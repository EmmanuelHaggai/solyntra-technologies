#!/usr/bin/env python3
"""
Debug script to identify which validation is failing for amount '10'
"""
from handlers import USSDHandlers

def test_validation_paths():
    print("Testing all validation paths for amount '10':")
    print("=" * 50)
    
    handlers = USSDHandlers()
    
    # Test 1: Direct handlers.validate_amount() with 10 (as sats)
    print("\n1. Testing validate_amount(10) - treating as sats:")
    valid, error = handlers.validate_amount(10)
    print(f"   Result: valid={valid}, error='{error}'")
    
    # Test 2: Direct handlers.validate_amount() with converted amount
    kes_to_sats = int(10 * (1000/150))  # 10 KES to sats
    print(f"\n2. Testing validate_amount({kes_to_sats}) - 10 KES converted to sats:")
    valid, error = handlers.validate_amount(kes_to_sats)
    print(f"   Result: valid={valid}, error='{error}'")
    
    # Test 3: Topup via mpesa function
    print(f"\n3. Testing topup_via_mpesa('+254712345678', 10):")
    success, message, data = handlers.topup_via_mpesa('+254712345678', 10)
    print(f"   Result: success={success}, message='{message}'")
    
    print("\n" + "=" * 50)
    print("Conclusions:")
    print("- If test 1 shows valid=False: App is incorrectly treating KES as sats")
    print("- If test 2 shows valid=True: Conversion is working correctly")  
    print("- If test 3 shows success=True: Handler itself is working correctly")

if __name__ == "__main__":
    test_validation_paths()