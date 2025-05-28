# 🚨 Authentication Issues Diagnosis & Fix Guide

## 📋 Current Status
Both authentication methods are failing:

### ❌ Application Permissions (bot.py)
- **Error**: `403 Authorization_RequestDenied`
- **Issue**: Missing admin consent or permissions
- **Current permissions likely missing**: Files.Read.All, User.Read.All

### ❌ Delegated Permissions (device code)
- **Error**: `AADSTS7000218: client_assertion or client_secret required`
- **Issue**: App configured as confidential client, not public client

## 🛠️ Fix Options

### Option 1: Fix Application Permissions (Recommended for Organization)

#### Step 1: Add Required Permissions
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Find your app: `6bb1d29e-c2cb-45a0-a37a-71832c7f5ad8`
4. Click **API permissions**
5. **Remove all existing permissions**
6. **Add these APPLICATION permissions**:
   - `Files.Read.All` (Application)
   - `Files.ReadWrite.All` (Application)
   - `Sites.Read.All` (Application)
   - `User.Read.All` (Application)

#### Step 2: Grant Admin Consent
1. Click **Grant admin consent for [Your Organization]**
2. Click **Yes** to confirm
3. Verify all permissions show **✅ Granted for [Your Organization]**

#### Step 3: Test
```bash
python simple_test.py
```

### Option 2: Fix Delegated Permissions (Easier Setup)

#### Step 1: Configure App as Public Client
1. In your Azure app → **Authentication**
2. Under **Advanced settings** → **Allow public client flows**: **Yes**
3. **Save**

#### Step 2: Add Delegated Permissions
1. Go to **API permissions**
2. **Remove all existing permissions**
3. **Add these DELEGATED permissions**:
   - `Files.Read` (Delegated)
   - `Files.ReadWrite` (Delegated)
   - `User.Read` (Delegated)
4. **Save** (no admin consent needed for delegated)

#### Step 3: Test
```bash
python simple_test.py
```

### Option 3: Create New App Registration (Fresh Start)

If the above don't work, create a new app:

1. Go to **Azure Active Directory** → **App registrations** → **New registration**
2. **Name**: `OneDrive-Telegram-Bot-v2`
3. **Supported account types**: Accounts in this organizational directory only
4. **Redirect URI**: Leave blank for now
5. Click **Register**

Then follow either Option 1 or Option 2 steps above.

## 🎯 Recommended Next Steps

1. **Try Option 1 first** (fix current app with application permissions)
2. **If you don't have admin rights**, try Option 2 (delegated permissions)
3. **If both fail**, try Option 3 (new app registration)

## 🧪 Testing Commands

After making changes, test with:
```bash
# Test both methods
python simple_test.py

# Test just application permissions
python test_graph.py

# Run the bot (if tests pass)
python bot.py
```

## 📞 Need Help?

If you don't have admin rights to grant consent:
1. Contact your IT administrator
2. Share this guide with them
3. Ask them to grant admin consent for the permissions listed above

The bot **will work** once the permissions are properly configured! 🚀
