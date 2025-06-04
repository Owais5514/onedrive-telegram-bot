# OneDrive Telegram Bot

A Python Telegram bot that provides access to OneDrive files and folders through an intuitive interface.

## Features

🎯 **Core Features:**
- Browse OneDrive files and folders through Telegram
- Download files directly to chat
- Fast navigation with local file indexing
- Real-time notifications for subscribers
- Admin management tools

🔧 **Technical Features:**
- Microsoft Graph API integration
- Dynamic inline keyboards
- Efficient file caching
- Background process management
- Secure authentication with Azure AD

## Setup

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Azure App Registration with OneDrive permissions

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository>
   cd onedrive-telegram-bot
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Azure App Registration:**
   - Create an app in Azure Portal
   - Add Microsoft Graph permissions: `Files.Read.All`
   - Generate client secret
   - Add credentials to `.env`

4. **Run the bot:**
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables (.env)
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
AZURE_CLIENT_ID=your_azure_client_id  
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=your_azure_tenant_id
ADMIN_USER_ID=your_telegram_user_id
TARGET_USER_ID=target_onedrive_user_id  # OneDrive user to access
```

### OneDrive Structure
The bot expects a "University" folder in the root of the specified user's OneDrive. All browsing starts from this folder.

## Usage

### User Commands
- `/start` - Start bot and show main menu
- `/help` - Show help information
- `/about` - About the bot
- `/privacy` - Privacy policy

### Admin Commands
- `/admin` - Admin panel (admin only)
  - Rebuild file index
  - Manage users
  - View bot statistics
  - Shutdown bot

### Navigation
1. Click "Browse Files" to start exploring
2. Navigate folders by clicking folder names
3. Click files to download them
4. Use "Back" button to navigate up
5. "Refresh Index" updates the file list

## Architecture

### File Structure

### GitHub Actions (Cloud Deployment) 🚀

This repository includes GitHub Actions workflows for automated cloud deployment:

**📋 Available Workflows:**
- **🤖 Manual Bot Runner** - Run bot on-demand with configurable duration
- **⏰ Scheduled Runner** - Automatic daily bot sessions  
- **🧪 Test & Build** - Continuous integration and testing

**⚡ Quick Setup:**
1. Fork this repository
2. Add secrets in Settings → Secrets and variables → Actions:
   - `TELEGRAM_BOT_TOKEN`
   - `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`
   - `USER_ID`, `ADMIN_USER_ID`
3. Go to Actions tab → "Run OneDrive Telegram Bot" → "Run workflow"

**📖 Complete Guide:** See [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) for detailed setup instructions, security best practices, and troubleshooting.

### Docker Deployment (Optional)
```bash
# Build and run with Docker
docker build -t onedrive-bot .
docker run -d --env-file .env onedrive-bot
```

## Architecture

### File Structure
```
bot.py              # Main bot implementation
indexer.py          # Standalone OneDrive indexing module
main.py             # Bot launcher script
troubleshoot.py     # Independent troubleshooting script
requirements.txt    # Python dependencies
.env.example        # Environment template
file_index.json     # Cached file structure
index_timestamp.txt # Index update timestamp
unlimited_users.json # Subscriber list
```

### Key Components
- **OneDriveBot**: Main bot class handling Telegram interactions
- **OneDriveIndexer**: Standalone module for OneDrive file indexing
- **File Indexing**: Local caching with smart refresh (1-hour TTL)
- **Authentication**: MSAL-based Azure AD integration with application permissions
- **Notifications**: Subscriber management and messaging

### Modular Design
The indexing logic is separated into a standalone module (`indexer.py`) that can be:
- Run independently for troubleshooting
- Called by the bot for file operations
- Used for manual index management
- Tested in isolation

```bash
# Run indexer independently
python indexer.py --stats           # Show statistics
python indexer.py --force           # Force rebuild index
python indexer.py --search "pdf"    # Search files

# Run troubleshooting script
python troubleshoot.py              # Run all diagnostic tests
```

## Security Features

🔒 **Security Measures:**
- Read-only OneDrive access
- Admin-only management commands
- Secure token management
- No file storage on bot server
- Encrypted user data

## Performance

⚡ **Optimizations:**
- Local file indexing for speed
- Token caching to reduce API calls
- Efficient folder navigation
- Background task management
- Minimal memory footprint

## Troubleshooting

### Independent Testing
Use the standalone indexer and troubleshooting tools:

```bash
# Test indexer functionality
python indexer.py --stats           # Show current index statistics
python indexer.py --force           # Force rebuild the entire index
python indexer.py --search "term"   # Search for files containing term

# Run comprehensive diagnostics
python troubleshoot.py              # Test all components systematically
```

### Common Issues
1. **"Access denied" errors**: 
   - Check Azure app permissions (Files.Read.All)
   - Verify TARGET_USER_ID is correct
   - Ensure application permissions (not delegated)

2. **"University folder not found"**: 
   - Ensure "University" folder exists in target user's OneDrive root
   - Check if TARGET_USER_ID has the correct OneDrive

3. **Bot not responding**: 
   - Verify Telegram bot token
   - Check network connectivity
   - Review logs for authentication errors

4. **File download failures**: 
   - Check file size limits (Telegram: 50MB)
   - Verify file permissions
   - Test with smaller files first

5. **Index not updating**:
   - Force rebuild with `python indexer.py --force`
   - Check index timestamp with `python indexer.py --stats`
   - Verify OneDrive API access

### Debug Mode
Set logging level in the scripts for detailed output:
```python
logging.getLogger().setLevel(logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Check the troubleshooting section
- Review logs when DEBUG=True
- Contact the admin through the bot

---

*Built with Python, Microsoft Graph API, and Telegram Bot API*
