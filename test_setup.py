#!/usr/bin/env python3
"""
Test script to verify the OneDrive Telegram Bot setup
"""

import os
import sys

def test_imports():
    """Test if all required packages can be imported"""
    print("🔍 Testing package imports...")
    
    try:
        import telegram
        print("✅ python-telegram-bot imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import python-telegram-bot: {e}")
        return False
    
    try:
        import msgraph
        print("✅ msgraph-sdk imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import msgraph-sdk: {e}")
        return False
    
    try:
        import azure.identity
        print("✅ azure-identity imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import azure-identity: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import python-dotenv: {e}")
        return False
    
    return True

def test_env_file():
    """Test if .env file exists and has required variables"""
    print("\n🔍 Testing environment configuration...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("💡 Create .env file from .env.example and add your credentials")
        return False
    
    print("✅ .env file exists")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['BOT_TOKEN', 'CLIENT_ID', 'CLIENT_SECRET', 'TENANT_ID']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            missing_vars.append(var)
        else:
            print(f"✅ {var} is set")
    
    if missing_vars:
        print(f"❌ Missing or placeholder values for: {', '.join(missing_vars)}")
        print("💡 Please update your .env file with actual credentials")
        return False
    
    return True

def test_bot_syntax():
    """Test if bot.py has valid syntax"""
    print("\n🔍 Testing bot.py syntax...")
    
    try:
        import ast
        with open('bot.py', 'r') as f:
            ast.parse(f.read())
        print("✅ bot.py syntax is valid")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in bot.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading bot.py: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 OneDrive Telegram Bot Setup Test\n")
    
    all_tests_passed = True
    
    # Test imports
    if not test_imports():
        all_tests_passed = False
        print("\n💡 Run: pip install -r requirements.txt")
    
    # Test environment
    if not test_env_file():
        all_tests_passed = False
        print("\n💡 Set up your .env file with proper credentials")
    
    # Test bot syntax
    if not test_bot_syntax():
        all_tests_passed = False
    
    print("\n" + "="*50)
    
    if all_tests_passed:
        print("🎉 All tests passed! Your bot is ready to run.")
        print("\n📖 Next steps:")
        print("1. Make sure your Azure app has proper permissions")
        print("2. Run: python bot.py")
        print("3. Test the bot in Telegram with /start")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\n📖 For help, check:")
        print("- README.md for detailed setup instructions")
        print("- QUICKSTART.md for quick setup guide")
    
    return all_tests_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
