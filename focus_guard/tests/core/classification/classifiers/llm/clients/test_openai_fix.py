#!/usr/bin/env python3
"""Quick test to verify OpenAI client fix."""

import os
import asyncio
from focus_guard.core.classification.classifiers.llm.openai_client import OpenAIClient

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise SystemExit("Set OPENAI_API_KEY to run this ad-hoc OpenAI client check.")

async def test_openai_client():
    """Test OpenAI client with gpt-5-nano."""
    
    client = OpenAIClient(model="gpt-4o-mini", max_tokens=512)
    
    prompt = """Classify this YouTube video for a 13-year-old student:
Title: Minecraft
Return valid JSON only with keys: category, usefulness, confidence, reason, is_distracting, content_type"""
    
    system_prompt = """You are a classifier. Return JSON with category (GAMING/EDUCATION/etc), usefulness (EDUCATIONAL/DISTRACTION/etc), confidence (0-1), reason (brief), is_distracting (true/false), content_type (video/shorts/etc)."""
    
    try:
        response = await client.generate(prompt, system_prompt)
        print(f"Response: {response}")
        print(f"Response type: {type(response)}")
        print(f"Response length: {len(response) if response else 0}")
        
        if response:
            print("SUCCESS: Got response from OpenAI")
            return True
        else:
            print("FAILED: No response from OpenAI")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_openai_client())
    print(f"Test result: {'PASS' if result else 'FAIL'}")
