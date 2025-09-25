#!/usr/bin/env python3
"""
OpenAI Account Status Checker
This script helps diagnose OpenAI API issues.
"""

import os
from openai import OpenAI

def check_openai_status():
    """Check OpenAI API status and account details."""
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print(" OPENAI_API_KEY environment variable not set")
        return False
    
    print(f" API Key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Test 1: Simple completion
        print("\n Testing basic completion...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use standard model first
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=5
        )
        print(" Basic completion works with gpt-3.5-turbo")
        
        # Test 2: Try gpt-5-nano specifically
        print("\n Testing gpt-5-nano model...")
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": "Say 'nano'"}],
            max_tokens=5
        )
        print(" gpt-5-nano works correctly")
        
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"\n Error: {error_str}")
        
        if "insufficient_quota" in error_str:
            print("\n BILLING ISSUE DETECTED:")
            print("   - Check your billing details at: https://platform.openai.com/account/billing")
            print("   - Verify payment method is valid")
            print("   - Check if you have available credits")
            print("   - Review usage limits in your account settings")
            
        elif "invalid_api_key" in error_str:
            print("\n API KEY ISSUE:")
            print("   - Verify your API key is correct")
            print("   - Check if the key has been revoked")
            
        elif "model_not_found" in error_str:
            print("\n MODEL ISSUE:")
            print("   - gpt-5-nano may not be available in your region/account")
            print("   - Try using gpt-4o-mini instead")
            
        return False

if __name__ == "__main__":
    print("OpenAI Account Status Checker")
    print("=" * 40)
    
    success = check_openai_status()
    
    if success:
        print("\nOpenAI API is working correctly!")
    else:
        print("\n OpenAI API has issues that need to be resolved.")
        print("\nNext steps:")
        print("1. Visit https://platform.openai.com/account/billing")
        print("2. Check your payment method and add credits if needed")
        print("3. Review your usage limits and increase if necessary")
