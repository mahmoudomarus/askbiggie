#!/usr/bin/env python3
"""
Simple test script to check Langfuse initialization
"""
import os
import sys

print("🧪 Testing Langfuse initialization...")
print(f"📄 Current environment variables:")
print(f"   LANGFUSE_PUBLIC_KEY: {os.getenv('LANGFUSE_PUBLIC_KEY', 'NOT SET')[:10]}...")
print(f"   LANGFUSE_SECRET_KEY: {os.getenv('LANGFUSE_SECRET_KEY', 'NOT SET')[:10]}...")
print(f"   LANGFUSE_HOST: {os.getenv('LANGFUSE_HOST', 'NOT SET')}")

try:
    print("\n🔧 Importing Langfuse service...")
    from services.langfuse import langfuse, enabled
    
    print(f"✅ Import successful!")
    print(f"   Enabled: {enabled}")
    print(f"   Langfuse instance: {langfuse}")
    
    if enabled and langfuse:
        print("🧪 Testing basic functionality...")
        trace = langfuse.trace(name="test_trace")
        print(f"   Test trace created: {trace}")
        
        print("🏁 Langfuse is working correctly!")
    else:
        print("⚠️ Langfuse is disabled or not properly initialized")
        
except Exception as e:
    print(f"❌ Error importing or testing Langfuse: {e}")
    import traceback
    traceback.print_exc() 