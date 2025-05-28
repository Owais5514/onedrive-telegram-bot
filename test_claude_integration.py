#!/usr/bin/env python3
"""
Test script for Claude AI integration
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_claude_integration():
    """Test Claude AI integration"""
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    
    if not claude_api_key:
        print("❌ CLAUDE_API_KEY not found in environment variables")
        print("Please set CLAUDE_API_KEY in your .env file")
        return False
    
    try:
        from anthropic import AsyncAnthropic
        
        # Initialize client
        client = AsyncAnthropic(api_key=claude_api_key)
        
        # Test simple message
        print("🔄 Testing Claude AI connection...")
        message = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Please respond with 'Claude AI is working correctly' to confirm the connection."
                }
            ]
        )
        
        response = message.content[0].text
        print(f"✅ Claude AI Response: {response}")
        
        if "working correctly" in response.lower():
            print("✅ Claude AI integration test PASSED!")
            return True
        else:
            print("⚠️ Claude AI responded but didn't give expected message")
            return False
            
    except ImportError:
        print("❌ Anthropic library not installed. Run: pip install anthropic")
        return False
    except Exception as e:
        print(f"❌ Error testing Claude AI: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_claude_integration())
