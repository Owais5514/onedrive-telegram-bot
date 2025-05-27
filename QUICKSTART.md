# Quick Start Guide

## 1. Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrSTUvwxyz`)

## 2. Set up Azure App Registration

### Step-by-step Azure Setup:

1. **Go to Azure Portal**: https://portal.azure.com
2. **Navigate to App Registrations**:
   - Search for "App registrations" in the top search bar
   - Click on "App registrations"

3. **Create New Registration**:
   - Click "New registration"
   - Name: `OneDrive Telegram Bot`
   - Supported account types: Select the appropriate option for your organization
   - Redirect URI: Leave blank for now
   - Click "Register"

4. **Note down IDs**:
   - Copy "Application (client) ID" → This is your `CLIENT_ID`
   - Copy "Directory (tenant) ID" → This is your `TENANT_ID`

5. **Create Client Secret**:
   - Go to "Certificates & secrets" in the left menu
   - Click "New client secret"
   - Description: `Telegram Bot Secret`
   - Expires: Choose appropriate duration (recommended: 24 months)
   - Click "Add"
   - **IMPORTANT**: Copy the secret value immediately → This is your `CLIENT_SECRET`

6. **Set API Permissions**:
   - Go to "API permissions" in the left menu
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Choose "Application permissions"
   - Find and select:
     - `Files.Read.All`
     - `Sites.Read.All` (optional, for SharePoint access)
   - Click "Add permissions"
   - **IMPORTANT**: Click "Grant admin consent for [your organization]"
   - Wait for the status to show "Granted"

## 3. Configure the Bot

1. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit .env file** with your credentials:
   ```
   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
   CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   CLIENT_SECRET=your_secret_value_here
   TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

## 4. Install and Run

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the bot**:
   ```bash
   python bot.py
   ```

3. **Test in Telegram**:
   - Find your bot by username
   - Send `/start`
   - Send `/browse` to start browsing files

## Troubleshooting Quick Fixes

### "Error accessing OneDrive"
- Make sure you clicked "Grant admin consent" in Azure
- Check that all permissions are granted (green checkmarks)
- Verify CLIENT_ID, CLIENT_SECRET, and TENANT_ID are correct

### "Missing required environment variables"
- Check your .env file exists in the project root
- Verify all four variables are set with actual values
- Make sure there are no extra spaces around the = signs

### "Authentication failed"
- Double-check your CLIENT_SECRET (it's only shown once in Azure)
- Verify TENANT_ID is correct
- Try creating a new client secret if the old one expired

### Bot doesn't respond
- Verify BOT_TOKEN is correct
- Make sure only one instance of the bot is running
- Check bot logs for error messages

## Need Help?

1. Check the full README.md for detailed instructions
2. Verify all Azure permissions are granted
3. Check the console output for specific error messages
4. Make sure your Azure app has the correct permissions for OneDrive access
