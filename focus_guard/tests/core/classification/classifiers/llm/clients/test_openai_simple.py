#!/usr/bin/env python3
"""
Simple OpenAI API Test
"""

import os
from openai import OpenAI

def test_openai():
    """Test OpenAI API with different models."""
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return False
    
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    
    client = OpenAI(api_key=api_key)
    
    # Test models in order of preference
    models_to_test = [
        "gpt-5-nano",
        "gpt-4o-mini", 
        "gpt-3.5-turbo"
    ]
    
    for model in models_to_test:
        try:
            print(f"\nTesting {model}...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=5
            )
            print(f"SUCCESS: {model} works - {response.choices[0].message.content}")
            return True
            
        except Exception as e:
            print(f"FAILED: {model} - {str(e)[:100]}...")
            if "insufficient_quota" in str(e):
                print("  -> Billing/quota issue detected")
            elif "model_not_found" in str(e):
                print("  -> Model not available")
            continue
    
    print("\nAll models failed. Check your OpenAI account:")
    print("1. https://platform.openai.com/account/billing")
    print("2. Verify payment method and credits")
    print("3. Check usage limits")
    return False

if __name__ == "__main__":
    test_openai()
