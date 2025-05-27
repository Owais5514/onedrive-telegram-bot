# OneDrive Telegram Bot

A Python Telegram bot that allows users to browse OneDrive files and folders directly through Telegram, with the ability to share files instantly.

## Features

- 🗂️ Browse OneDrive files and folders in a user-friendly interface
- 📁 Navigate through folders with inline keyboard buttons (2-column layout)
- 📄 Share files directly in Telegram chat with download links
- ⬅️ Easy navigation with back and home buttons
- 🔒 Secure authentication using Microsoft Graph API

## Prerequisites

Before setting up the bot, you need:

1. **Telegram Bot Token**
   - Create a new bot using [@BotFather](https://t.me/BotFather) on Telegram
   - Get your bot token

2. **Azure App Registration**
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to "Azure Active Directory" > "App registrations" > "New registration"
   - Set up your app with the following permissions:
     - `Files.Read.All` (Application permission)
     - `Sites.Read.All` (Application permission)
   - Note down: Client ID, Client Secret, and Tenant ID

## Installation

1. Clone or download this repository:
   ```bash
   git clone <repository-url>
   cd onedrive-telegram-bot
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create environment configuration:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with your credentials:
   ```env
   BOT_TOKEN=your_telegram_bot_token_here
   CLIENT_ID=your_azure_app_client_id_here
   CLIENT_SECRET=your_azure_app_client_secret_here
   TENANT_ID=your_azure_tenant_id_here
   ```

## Azure App Setup (Detailed)

1. **Register Application:**
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to "Azure Active Directory" > "App registrations"
   - Click "New registration"
   - Name: "OneDrive Telegram Bot"
   - Supported account types: "Accounts in this organizational directory only"
   - Click "Register"

2. **Configure API Permissions:**
   - Go to "API permissions" in your app
   - Click "Add a permission"
   - Select "Microsoft Graph" > "Application permissions"
   - Add these permissions:
     - `Files.Read.All`
     - `Sites.Read.All` (if accessing SharePoint)
   - Click "Grant admin consent"

3. **Create Client Secret:**
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Add description and set expiration
   - Copy the secret value (you won't see it again!)

4. **Note the IDs:**
   - Copy "Application (client) ID" from Overview page
   - Copy "Directory (tenant) ID" from Overview page

## Usage

1. Start the bot:
   ```bash
   python bot.py
   ```

2. In Telegram, start a conversation with your bot:
   - Send `/start` to see the welcome message
   - Send `/browse` to start browsing OneDrive files
   - Send `/current` to see your current folder path

3. **Navigation:**
   - Click on folder buttons (📁) to enter folders
   - Click on file buttons (📄) to get download links
   - Use "⬅️ Back" to go to parent folder
   - Use "🏠 Home" to return to root folder

## Bot Commands

- `/start` - Show welcome message and bot information
- `/browse` - Start browsing OneDrive files and folders
- `/current` - Show current folder path

## File Structure

```
onedrive-telegram-bot/
├── bot.py              # Main bot application
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
├── .env              # Your actual environment variables (create this)
└── README.md         # This file
```

## Troubleshooting

### Common Issues:

1. **"Missing required environment variables"**
   - Make sure your `.env` file exists and contains all required variables
   - Check that variable names match exactly

2. **"Error accessing OneDrive"**
   - Verify your Azure app has the correct permissions
   - Ensure admin consent was granted for the permissions
   - Check that Client Secret hasn't expired

3. **"Bot doesn't respond"**
   - Verify your Telegram bot token is correct
   - Make sure the bot is not already running elsewhere

4. **"Authentication failed"**
   - Double-check Client ID, Client Secret, and Tenant ID
   - Ensure the Azure app is configured correctly

### Debug Mode:

Set `DEBUG=True` in your `.env` file to enable detailed logging.

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Azure client secrets have expiration dates - monitor and renew them
- The bot uses application permissions, so it can access OneDrive on behalf of the organization
- Download links are temporary and expire automatically

## Dependencies

- `python-telegram-bot` - Telegram Bot API wrapper
- `msgraph-sdk` - Microsoft Graph SDK for Python
- `azure-identity` - Azure authentication library
- `python-dotenv` - Environment variable management
- `asyncio` - Asynchronous programming support
- `aiohttp` - HTTP client for async operations

## License

This project is provided as-is for educational and personal use. Make sure to comply with Microsoft's API terms of service and Telegram's bot guidelines.

## Contributing

Feel free to submit issues and enhancement requests. Pull requests are welcome!

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Review the Azure app configuration
3. Ensure all dependencies are installed correctly
4. Check the bot logs for specific error messages