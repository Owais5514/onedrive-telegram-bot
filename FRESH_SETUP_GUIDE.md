# 🚀 Fresh Azure App Setup - Option 1 (Application Permissions)

## Step 1: Create New Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**

### Registration Details:
- **Name**: `OneDrive-Telegram-Bot-Fresh`
- **Supported account types**: `Accounts in this organizational directory only`
- **Redirect URI**: Leave blank
- Click **Register**

## Step 2: Note Down Credentials

After registration, you'll see:
- **Application (client) ID**: Copy this
- **Directory (tenant) ID**: Copy this

Then:
1. Go to **Certificates & secrets**
2. Click **New client secret**
3. **Description**: `Bot Secret`
4. **Expires**: `24 months`
5. Click **Add**
6. **Copy the secret value immediately** (you won't see it again)

## Step 3: Configure API Permissions

1. Go to **API permissions**
2. Remove the default `User.Read` permission
3. Click **Add a permission**
4. Choose **Microsoft Graph**
5. Select **Application permissions**
6. Add these permissions:
   - `Files.Read.All`
   - `Files.ReadWrite.All`
   - `Sites.Read.All`
   - `User.Read.All`
7. Click **Add permissions**

## Step 4: Grant Admin Consent

🚨 **CRITICAL STEP**:
1. Click **Grant admin consent for [Your Organization]**
2. Click **Yes** in the confirmation dialog
3. Verify all permissions show **✅ Granted for [Your Organization]**

## Step 5: Update Environment Variables

Update your `.env` file with the new credentials:

```env
# Telegram Bot Token (keep existing)
TELEGRAM_BOT_TOKEN=6963034827:AAGBtg0IClx60JPqPLPpQMe6EiyXNYI8-nM

# NEW Azure App Registration details
AZURE_CLIENT_ID=your-new-client-id-here
AZURE_CLIENT_SECRET=your-new-client-secret-here
AZURE_TENANT_ID=your-tenant-id-here
```

## Step 6: Test the Setup

```bash
python simple_test.py
```

Should show:
```
✅ Application permissions: WORKING
🚀 Use: python bot.py
```

## 🔍 Common Issues & Solutions

### Issue: "Grant admin consent" button is grayed out
- **Solution**: You need Global Administrator or Application Administrator role
- **Workaround**: Ask your IT admin to grant consent

### Issue: Still getting 403 errors
- **Check**: All 4 permissions are added with "Application" type (not Delegated)
- **Check**: Admin consent shows "Granted" status
- **Wait**: Sometimes takes 5-10 minutes to propagate

### Issue: Can't create app registration
- **Solution**: You need Application Developer role or higher
- **Workaround**: Ask IT admin to create the app for you

## 🎯 Success Criteria

When working correctly, you should see:
1. ✅ Graph client initialized
2. ✅ Access to organization users
3. ✅ OneDrive file listing works
4. ✅ Bot responds with real OneDrive data

Ready to proceed? Follow the steps above and update your `.env` file with the new credentials!
