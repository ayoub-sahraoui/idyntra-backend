"""
Quick test runner for verification API
Run this to quickly test the main vulnerability
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

if __name__ == "__main__":
    # Run the same-image attack test to verify the fix
    print("\n" + "="*70)
    print("TESTING SAME-IMAGE ATTACK VULNERABILITY FIX")
    print("="*70 + "\n")
    
    exit_code = pytest.main([
        "tests/test_verification_scenarios.py::TestVerificationAPI::test_same_image_attack",
        "-v",
        "-s",
        "--tb=short"
    ])
    
    if exit_code == 0:
        print("\n" + "="*70)
        print("✅ TEST PASSED - Same-image attack is now properly rejected!")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("❌ TEST FAILED - Review the output above")
        print("="*70 + "\n")
    
    sys.exit(exit_code)
