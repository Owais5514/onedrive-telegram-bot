# OneDrive Telegram Bot

A Python Telegram bot that allows users to browse OneDrive files and folders directly through Telegram, with the ability to download files instantly.

## Features

- 🗂️ Browse OneDrive files and folders in a user-friendly interface
- 📁 Navigate through folders with inline keyboard buttons 
- 📄 Download files directly to Telegram chat
- ⬅️ Easy navigation with back and home buttons
- 🔒 Secure authentication using Microsoft Graph API
- 🎯 Configurable folder restrictions (default: University folder only)
- 👥 Multi-user support with automatic user selection

## Prerequisites

Before setting up the bot, you need:

1. **Telegram Bot Token**
   - Create a new bot using [@BotFather](https://t.me/BotFather) on Telegram
   - Get your bot token

2. **Azure App Registration**
   - Go to [Azure Portal](https://portal.azure.com)
   - Create an app registration with Application permissions
   - Note down: Client ID, Client Secret, and Tenant ID

## Quick Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file with your credentials:**
   ```env
   # Telegram Bot
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

   # Azure App Registration
   AZURE_CLIENT_ID=your_azure_client_id_here
   AZURE_CLIENT_SECRET=your_azure_client_secret_here
   AZURE_TENANT_ID=your_azure_tenant_id_here
   ```

4. **Run the bot:**
   ```bash
   python bot_continuous.py
   ```

## Azure Permissions Required

Your Azure app needs these **Application permissions**:
- `Files.Read.All` - Read all files in organization
- `User.Read.All` - Read all user profiles

Make sure to **Grant admin consent** for these permissions in the Azure portal.

## Usage

1. Start a chat with your bot on Telegram
2. Send `/start` to begin browsing OneDrive
3. Use the inline buttons to navigate folders and download files
4. The bot is restricted to the "University" folder by default for security

## Configuration

The bot can be configured by modifying variables in `bot_continuous.py`:
- `base_folder`: Change the restricted folder (default: "University")
- `restricted_mode`: Enable/disable folder restrictions (default: True)

## File Structure

```
onedrive-telegram-bot/
├── bot_continuous.py   # Main bot application
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
├── .env              # Your actual environment variables
└── README.md         # This documentation
```

## Troubleshooting

If you encounter issues:
1. Verify your Azure app has the correct permissions and admin consent
2. Check that all environment variables are set correctly
3. Ensure your Telegram bot token is valid
4. Check the console output for detailed error messages

## Dependencies

- `python-telegram-bot==20.7` - Telegram Bot API wrapper
- `msgraph-sdk==1.5.4` - Microsoft Graph SDK for Python
- `azure-identity==1.15.0` - Azure authentication library
- `python-dotenv==1.0.0` - Environment variable management
- `asyncio` - Asynchronous programming support
- `aiohttp` - HTTP client for async operations

## Security Notes

- The bot is restricted to the "University" folder by default for security
- Download links are temporary and expire automatically
- Keep your `.env` file secure and never commit it to version control
- Azure client secrets have expiration dates - monitor and renew them