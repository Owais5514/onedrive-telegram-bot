# Azure OneDrive Permissions Setup Guide

## 🚨 Current Issue: Authorization_RequestDenied

Your bot is getting "Insufficient privileges to complete the operation" errors. This means the Azure app needs proper permissions setup.

## 🛤️ Two Authentication Approaches

### Option 1: Application Permissions (Current - Having Issues)
- ❌ Requires admin consent for organization
- ❌ Complex permission setup
- ❌ Currently failing with 403 errors
- ✅ Works for organization-wide access

### Option 2: Delegated Permissions (Recommended)
- ✅ Easier to set up
- ✅ No admin consent required
- ✅ Works with personal OneDrive
- ⚠️ Requires user authentication each time

## 🔧 Quick Fix: Switch to Delegated Permissions

### Step 1: Update Azure App Registration
1. Go to [Azure Portal](https://portal.azure.com) → **App registrations**
2. Find your app → **API permissions**
3. **Remove all current permissions**
4. **Add these delegated permissions**:
   - `Files.Read` (Delegated)
   - `Files.ReadWrite` (Delegated) 
   - `User.Read` (Delegated)
5. **Save** (no admin consent needed for delegated)

### Step 2: Update Redirect URI
1. In your app → **Authentication**
2. Add redirect URI: `http://localhost:8000/auth/callback`
3. Save

### Step 3: Test the New Approach
```bash
# Test delegated authentication
python test_delegated_auth.py

# Run bot with delegated permissions
python bot_delegated.py
```

## 🔍 Troubleshooting Current Application Permissions

If you want to keep using application permissions, try these steps:

### 1. Verify Permissions Are Added
In Azure Portal → Your App → API permissions:
- ✅ `Files.Read.All` (Application)
- ✅ `Files.ReadWrite.All` (Application)  
- ✅ `Sites.Read.All` (Application)
- ✅ `User.Read.All` (Application)

### 2. Check Admin Consent Status
- All permissions should show "Granted for [Organization]"
- If not, click **Grant admin consent** button
- You may need Global Admin privileges

### 3. Alternative Endpoints to Try
Instead of `/users/{id}/drive`, try:
- `/me/drive` (if using delegated)
- `/drives` (list all drives)
- `/sites/{site-id}/drive` (specific site)

### 4. Check Tenant Settings
Your organization might block application permissions:
- Contact your IT admin
- Check Azure AD security policies
- Verify app registration isn't restricted

## 🎯 Recommended Next Steps

1. **Try delegated permissions first** (easier setup)
2. If that works, you can keep using `bot_delegated.py`
3. If you need application permissions, contact your IT admin

## 📋 Files in Your Project

- `bot.py` - Original bot with application permissions
- `bot_delegated.py` - New bot with delegated permissions  
- `test_graph.py` - Tests application permissions
- `test_delegated_auth.py` - Tests delegated permissions

## 🚀 Quick Start with Delegated Permissions

```bash
# 1. Update Azure permissions (delegated instead of application)
# 2. Add redirect URI: http://localhost:8000/auth/callback
# 3. Run the delegated version:
python bot_delegated.py
```

The delegated approach will prompt you to log in via browser, but then should work immediately without complex permission setup!
