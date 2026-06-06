#!/usr/bin/env python3
"""
Test script to verify Sarvam API reachability and LLM response
"""
import os
import sys
from dotenv import find_dotenv, load_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Test 1: Check if API key is set
print("=" * 60)
print("TEST 1: Checking API Key Configuration")
print("=" * 60)

api_key = os.getenv("SARVAM_API_KEY")
if not api_key:
    print("❌ SARVAM_API_KEY not found in environment")
    sys.exit(1)

print(f"✓ API Key found: {api_key[:10]}...{api_key[-5:]}")

# Test 2: Check API endpoint reachability
print("\n" + "=" * 60)
print("TEST 2: Checking API Endpoint Reachability")
print("=" * 60)

import requests

url = "https://api.sarvam.ai/v1/chat/completions"
print(f"Testing endpoint: {url}")

try:
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=5
    )
    print(f"✓ Endpoint is reachable (Status: {response.status_code})")
except requests.exceptions.ConnectionError:
    print("❌ Connection error - API endpoint unreachable")
    sys.exit(1)
except requests.exceptions.Timeout:
    print("❌ Timeout - API endpoint not responding")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 3: Test LLM with a simple request
print("\n" + "=" * 60)
print("TEST 3: Testing LLM Response")
print("=" * 60)

try:
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(
        model="sarvam-m",
        api_key=api_key,
        base_url="https://api.sarvam.ai/v1",
        temperature=0.3,
    )
    
    print("Sending test prompt to sarvam-m model...")
    response = llm.invoke("What is 2+2? Reply in one line.")
    
    print(f"✓ LLM Response received:")
    print(f"  {response.content}")
    
except Exception as e:
    print(f"❌ LLM Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test with Hindi language (app's target use case)
print("\n" + "=" * 60)
print("TEST 4: Testing Hindi Language Support")
print("=" * 60)

try:
    print("Sending Hindi prompt to test language support...")
    response = llm.invoke("नमस्ते! क्या आप हिंदी में बात कर सकते हैं?")
    
    print(f"✓ Hindi Response received:")
    print(f"  {response.content}")
    
except Exception as e:
    print(f"❌ Hindi Language Test Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)
print("\nSarvam API is reachable and responding correctly.")
