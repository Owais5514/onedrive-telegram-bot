# Azure OneDrive Permissions Setup Guide

## 🔑 Required Permissions for OneDrive Access

Your bot currently uses **mock data** because the required OneDrive permissions are not properly configured. Follow this guide to enable real OneDrive file access.

## 📋 Current Status
- ✅ Bot is working with mock data
- ❌ Real OneDrive access requires permission setup
- ❌ Application permissions need admin consent

## 🚀 Step-by-Step Setup

### 1. Go to Azure Portal
1. Visit [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Find your app (the one with Client ID from your .env file)

### 2. Configure API Permissions
Click on **API permissions** in the left sidebar:

#### Required Permissions:
- `Files.Read.All` (Application) - Read all files in all site collections
- `Files.ReadWrite.All` (Application) - Read and write all files in all site collections  
- `Sites.Read.All` (Application) - Read items in all site collections
- `User.Read.All` (Application) - Read all users' profiles

#### How to Add:
1. Click **Add a permission**
2. Choose **Microsoft Graph**
3. Select **Application permissions** (not Delegated)
4. Search for and add each permission listed above
5. Click **Add permissions**

### 3. Grant Admin Consent
**CRITICAL:** After adding permissions:
1. Click **Grant admin consent for [Your Organization]**
2. Click **Yes** to confirm
3. Verify all permissions show **Granted for [Your Organization]**

### 4. API Endpoints Used
The bot uses these Microsoft Graph endpoints:
```
GET /users
GET /users/{user-id}/drive/root/children
GET /users/{user-id}/drive/root/item-with-path('{path}')/children
GET /users/{user-id}/drive/items/{item-id}
```

## 🔧 Testing the Setup

After configuring permissions, test the connection:

```bash
cd /workspaces/onedrive-telegram-bot
python test_graph.py
```

## ⚠️ Important Notes

1. **Application vs Delegated Permissions:**
   - Bot uses Application permissions (acts as itself)
   - No user login required in the bot
   - Admin consent is mandatory

2. **User Access:**
   - Bot will access the first user found in your tenant
   - For production, specify exact user ID in the code

3. **File Access:**
   - Bot can read all OneDrive files for the user
   - University folder will be used as the starting point
   - If University folder doesn't exist, root folder will be used

## 🐛 Troubleshooting

### Common Issues:

**"Insufficient privileges" Error:**
- Admin consent not granted
- Missing required permissions
- Wrong permission type (Delegated vs Application)

**"No users found" Error:**
- User.Read.All permission missing
- Admin consent not granted

**"BadRequest /me not valid" Error:**
- Trying to use /me endpoint with application permissions
- Code has been updated to use /users/{id} instead

## 📱 Once Setup is Complete

After proper permissions are configured:
1. Real OneDrive files will replace mock data
2. Actual folder navigation will work
3. Real file downloads will be available
4. University folder contents will be displayed

## 🔄 Fallback Behavior

Until permissions are set up:
- Bot uses mock data for demonstration
- All navigation features work
- Interface is fully functional
- Mock files show how real files would appear

**The bot interface is complete and ready - only the OneDrive backend needs proper permissions!**
