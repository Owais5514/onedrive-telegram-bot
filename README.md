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
- 🤖 **AI-powered file search** using Claude AI
- 🔄 **Smart rate limiting** (1 query per day for regular users)
- 👑 **Unlimited access** management for premium users
- 💬 **Group chat support** with ephemeral messages
- ⏰ **Auto-deletion** of bot messages in groups (5 minutes after last interaction)

## Prerequisites

Before setting up the bot, you need:

1. **Telegram Bot Token**
   - Create a new bot using [@BotFather](https://t.me/BotFather) on Telegram
   - Get your bot token

2. **Azure App Registration**
   - Go to [Azure Portal](https://portal.azure.com)
   - Create an app registration with Application permissions
   - Note down: Client ID, Client Secret, and Tenant ID

3. **Claude AI API (Optional)**
   - Get API key from [Anthropic](https://console.anthropic.com/)
   - Required for AI file search feature (uses Claude 3.5 Sonnet)

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
   
   # Claude AI API (Optional - for AI file search)
   CLAUDE_API_KEY=your_claude_api_key_here
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
4. Click "🤖 AI Search" to search files using natural language
5. In groups, bot messages will auto-delete after 5 minutes of inactivity
6. Regular users get 1 AI search per day; admins can grant unlimited access

### AI Search Examples
- "Find my calculus notes"
- "Show me Python programming files"
- "Look for semester 1 assignments"
- "Search for presentation slides"

### Admin Commands
- `/admin add_unlimited <user_id>` - Grant unlimited AI searches
- `/admin remove_unlimited <user_id>` - Remove unlimited access
- `/admin list_unlimited` - List users with unlimited access
- `/admin rebuild_index` - Rebuild the file search index

## Static Web Interface

A static web interface is available to browse your OneDrive contents. It uses a pre-generated JSON index (`docs/onedrive_index.json`) and runs entirely in your web browser, making it suitable for hosting on platforms like GitHub Pages.

### Generating the File/Folder Index (`onedrive_index.json`)

The `generate_onedrive_index.py` script is responsible for creating the JSON index file that the web interface uses.

**Prerequisites:**
- Python 3.x installed.
- Dependencies from `requirements.txt` installed. Run:
  ```bash
  pip install -r requirements.txt
  ```
- A `.env` file must be present in the root directory, configured with your Azure application credentials:
  - `AZURE_CLIENT_ID`
  - `AZURE_CLIENT_SECRET`
  - `AZURE_TENANT_ID`
  (This is the same `.env` file and credentials used by the Telegram bot.)

**Running the script:**
Execute the script from the root of the repository:
```bash
python generate_onedrive_index.py
```
This will create or update the `docs/onedrive_index.json` file.

**Configuration Options:**
The script has a few configurable options at the top:
- `DEFAULT_BASE_FOLDER`: Specifies the root folder to start indexing from (defaults to "University"). This can also be set via the `ONEDRIVE_BASE_FOLDER` environment variable.
- `DEFAULT_RESTRICTED_MODE`: If `True` (default), indexing is confined to the `DEFAULT_BASE_FOLDER`. If `False`, it attempts to index the entire OneDrive. This can also be set via the `ONEDRIVE_RESTRICTED_MODE` environment variable (e.g., `ONEDRIVE_RESTRICTED_MODE=false`).
- `PREFERRED_USER_DISPLAY_NAME`: If you have multiple users under your Azure AD, you can set this to the display name of the user whose OneDrive you want to index (defaults to "Owais Ahmed").

### Viewing the Web Interface

Once `docs/onedrive_index.json` has been generated:
1.  Open the `docs/index.html` file in your web browser.
2.  If you are using GitHub Pages, configure the `docs` folder as your publishing source. The interface will then be accessible via your GitHub Pages URL (e.g., `https://<username>.github.io/<repositoryname>/`).

### Functionality

The web interface allows you to:
- Browse the folder structure defined in `onedrive_index.json`.
- Navigate into subfolders.
- View files listed within folders.
- Click on a file to open its corresponding `webUrl` from OneDrive (this will usually prompt a download or display the file if supported by the browser/OneDrive).
- Use breadcrumbs for easy navigation back to parent folders or Home.

It is a read-only viewer and does not allow any modifications to your OneDrive content.

### Automated Updates

To keep the data for the static web interface current, a GitHub Action is set up to automatically regenerate the `docs/onedrive_index.json` file daily. This process helps ensure that the web view reflects recent changes in OneDrive.

**Manual Trigger:**

You can also manually trigger this update process:
1.  Navigate to the **Actions** tab of this repository on GitHub.
2.  Find the workflow named **"Update OneDrive Index"** in the list.
3.  Click on the workflow, and then use the **"Run workflow"** button (this option is available because `workflow_dispatch` is enabled).

**Repository Secrets:**

For the GitHub Action to successfully authenticate with OneDrive and generate the index, the following secrets must be configured in your repository's settings (under `Settings > Secrets and variables > Actions`):
*   `AZURE_CLIENT_ID`
*   `AZURE_CLIENT_SECRET`
*   `AZURE_TENANT_ID`
*   Optionally, `ONEDRIVE_BASE_FOLDER` and `ONEDRIVE_RESTRICTED_MODE` if you wish to override the script's default configurations via secrets. For example, you might set `ONEDRIVE_RESTRICTED_MODE` to `false` if your `ONEDRIVE_BASE_FOLDER` is set to the root or is empty.

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
- `anthropic==0.31.2` - Claude AI API client (optional)

## Security Notes

- The bot is restricted to the "University" folder by default for security
- Download links are temporary and expire automatically
- Keep your `.env` file secure and never commit it to version control
- Azure client secrets have expiration dates - monitor and renew them