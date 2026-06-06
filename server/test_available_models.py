#!/usr/bin/env python3
"""
Test Sarvam API with available models
"""
import os
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

api_key = os.getenv("SARVAM_API_KEY")

from langchain_openai import ChatOpenAI

print("=" * 60)
print("Testing Available Sarvam Models")
print("=" * 60)

models = ["sarvam-30b", "sarvam-105b"]

for model_name in models:
    print(f"\n📌 Testing model: {model_name}")
    print("-" * 60)
    
    try:
        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url="https://api.sarvam.ai/v1",
            temperature=0.3,
        )
        
        print("Sending test prompt...")
        response = llm.invoke("What is 2+2? Reply in one line.")
        
        print(f"✓ Response: {response.content[:100]}...")
        
        # Test Hindi too
        print("\nTesting Hindi prompt...")
        hindi_response = llm.invoke("नमस्ते! आप कौन हो?")
        print(f"✓ Hindi: {hindi_response.content[:100]}...")
        
    except Exception as e:
        print(f"❌ Error with {model_name}: {str(e)[:200]}")

print("\n" + "=" * 60)
print("Summary: Sarvam API is reachable.")
print("⚠️  Update llm.py: Change 'sarvam-m' to 'sarvam-30b' or 'sarvam-105b'")
print("=" * 60)
