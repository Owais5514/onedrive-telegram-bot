# 🔧 Azure App Permissions Setup Guide

## Current Issue
Your Azure app needs proper permissions to access OneDrive. The error "Insufficient privileges" means the app doesn't have the right permissions or admin consent.

## Required Permissions for OneDrive Telegram Bot

### Option 1: Delegated Permissions (Recommended for Personal Bot)
For a bot that accesses your own OneDrive:

1. **Go to Azure Portal** → Your App → **API Permissions**
2. **Add these DELEGATED permissions**:
   - `Files.Read` - Read user files
   - `Files.Read.All` - Read all files user can access  
   - `Files.ReadWrite` - Read and write user files (if you want upload features)
   - `User.Read` - Read user profile

3. **Grant Admin Consent** (click the "Grant admin consent" button)

### Option 2: Application Permissions (For Organization-wide Bot)
For a bot that accesses any user's OneDrive in your organization:

1. **Add these APPLICATION permissions**:
   - `Files.Read.All` - Read all files in organization
   - `Files.ReadWrite.All` - Read/write all files (if needed)
   - `User.Read.All` - Read all user profiles

2. **Grant Admin Consent** (required for application permissions)

## Current Status Check

Let's check what permissions your app currently has:

1. Go to: https://portal.azure.com
2. Navigate to: App registrations → Your app → API permissions
3. Look for:
   - ✅ Microsoft Graph permissions listed
   - ✅ Green checkmarks showing "Granted" status
   - ✅ "Granted for [your organization]" text

## Quick Fix Steps

1. **Add Missing Permissions**:
   ```
   Microsoft Graph → Delegated → Files.Read.All
   Microsoft Graph → Delegated → User.Read
   ```

2. **Grant Admin Consent**:
   - Click "Grant admin consent for [organization]"
   - Wait for green checkmarks

3. **Test Again**:
   ```bash
   python test_graph.py
   ```

## Permission Comparison

| Permission Type | Use Case | Requires Admin | Access Level |
|----------------|----------|----------------|--------------|
| Delegated | Personal bot | Maybe | User's files only |
| Application | Organization bot | Yes | All users' files |

## For This Bot
Since this is likely a personal Telegram bot, **Delegated permissions** are recommended.

## After Fixing
Run the test again to verify the permissions work.
