# 🔧 Azure Client Secret Setup Guide

## The Issue
Your current CLIENT_SECRET appears to be a Secret ID (UUID format like: 3e14c75a-f806-4967-abe8-03e7ea7b23fb)
But you need the actual Secret VALUE (a longer string with letters, numbers, and symbols)

## How to Fix This:

### Option 1: Get the Secret Value (if you still have it)
When you created the client secret, Azure showed you TWO things:
- **Secret ID**: 3e14c75a-f806-4967-abe8-03e7ea7b23fb (this is what you currently have)
- **Value**: A longer string like "8Q~abc123xyz..." (this is what you need)

If you still have the Value from when you created it, use that instead.

### Option 2: Create a New Client Secret (recommended)
Since client secret values are only shown once, you'll likely need to create a new one:

1. **Go to Azure Portal**: https://portal.azure.com
2. **Navigate to your app**: App registrations → Your app (OneDrive Telegram Bot)
3. **Go to Certificates & secrets** (left sidebar)
4. **Create new secret**:
   - Click "New client secret"
   - Description: "Telegram Bot Secret v2"
   - Expires: Choose duration (12-24 months recommended)
   - Click "Add"

5. **IMMEDIATELY copy the Value**:
   ```
   Secret ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  ← DON'T use this
   Value: 8Q~abc123xyz...                           ← USE THIS ONE!
   ```

6. **Update your .env file** with the new Value

## What the Secret Value looks like:
- ✅ Correct: `8Q~abc123xyz789.def456_ghi`
- ❌ Wrong: `3e14c75a-f806-4967-abe8-03e7ea7b23fb`

## Security Note:
- The secret Value is only shown ONCE when created
- Copy it immediately and store it securely
- Never share it or commit it to version control

## After fixing:
Run `python test_graph.py` again to verify the connection works.
