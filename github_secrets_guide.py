#!/usr/bin/env python3
"""
GitHub Secrets Verification Guide
Shows exactly which secrets need to be configured in GitHub repository
"""

print("🔧 GitHub Repository Secrets Configuration Guide")
print("=" * 60)
print()
print("Based on your .env.example file, you need to configure these secrets in your GitHub repository:")
print()
print("📍 Go to: GitHub Repository → Settings → Secrets and variables → Actions")
print()
print("🔑 Required Repository Secrets:")
print("   1. TELEGRAM_BOT_TOKEN")
print("   2. AZURE_CLIENT_ID")
print("   3. AZURE_CLIENT_SECRET")  
print("   4. AZURE_TENANT_ID")
print("   5. TARGET_USER_ID")
print("   6. ADMIN_USER_ID")
print()
print("📋 Copy these exact names when creating secrets:")
print("   • TELEGRAM_BOT_TOKEN")
print("   • AZURE_CLIENT_ID")
print("   • AZURE_CLIENT_SECRET")
print("   • AZURE_TENANT_ID")
print("   • TARGET_USER_ID")
print("   • ADMIN_USER_ID")
print()
print("💡 These match the variable names in your .env.example file exactly!")
