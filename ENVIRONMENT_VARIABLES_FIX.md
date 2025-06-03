# GitHub Actions Environment Variables Fix

## Issue Description
The GitHub Actions workflows were failing with `TENANT_ID is None` error because environment variables weren't being properly passed to the Python processes.

## Root Cause
The workflows were creating a `.env` file with secrets but not explicitly passing environment variables to each Python process step. While `python-dotenv` was installed and `load_dotenv()` was called in the code, the environment variables weren't being reliably loaded in the GitHub Actions environment.

## Solution Applied

### 1. Enhanced Environment Variable Passing
- Added explicit `env:` blocks to all Python execution steps in workflows
- Environment variables are now passed directly to each process instead of relying solely on `.env` file

### 2. Added Debug Capabilities
- Created `debug_env.py` script to troubleshoot environment variable issues
- Added debug step to workflows to verify environment variables before bot execution
- Enhanced logging in `.env` file creation to show which variables are being set

### 3. Improved Error Reporting
- Enhanced environment variable validation steps in workflows
- Added better error messages with troubleshooting hints
- Added partial value display for debugging (first 5 and last 3 characters)

## Files Modified

### `/workspaces/onedrive-telegram-bot/.github/workflows/run-bot.yml`
- Added `env:` blocks to all Python execution steps
- Enhanced environment file creation with debug output
- Added debug environment variables step

### `/workspaces/onedrive-telegram-bot/.github/workflows/scheduled-bot.yml`
- Added `env:` blocks to all Python execution steps
- Added debug environment variables step

### `/workspaces/onedrive-telegram-bot/debug_env.py` (NEW)
- Environment variable debugging utility
- Checks for both primary and alternative naming conventions
- Validates `.env` file existence and contents
- Provides detailed troubleshooting information

## Environment Variables Required
The following secrets must be configured in GitHub repository settings:

- `TELEGRAM_BOT_TOKEN` - Telegram bot token from BotFather
- `CLIENT_ID` - Azure App Registration Client ID
- `CLIENT_SECRET` - Azure App Registration Client Secret
- `TENANT_ID` - Azure Tenant ID
- `USER_ID` - OneDrive user email address
- `ADMIN_USER_ID` - Telegram admin user ID

## Alternative Naming Support
The indexer also supports these alternative environment variable names:
- `AZURE_CLIENT_ID` (alternative to `CLIENT_ID`)
- `AZURE_CLIENT_SECRET` (alternative to `CLIENT_SECRET`)
- `AZURE_TENANT_ID` (alternative to `TENANT_ID`)
- `TARGET_USER_ID` (alternative to `USER_ID`)

## Testing the Fix

### Local Testing
```bash
# Test environment variables locally
python debug_env.py

# Test indexer with current environment
python indexer.py --stats
```

### GitHub Actions Testing
1. Configure all required secrets in repository settings
2. Trigger "Run Bot Manually" workflow
3. Check the "Debug environment variables" step output
4. Verify all environment variables are properly loaded

## Expected Workflow Output
After applying this fix, the GitHub Actions logs should show:
```
✅ All required secrets are configured
🔍 Environment Variable Debug Information
✅ TELEGRAM_BOT_TOKEN: bot12...345
✅ CLIENT_ID: abcd...xyz
✅ CLIENT_SECRET: pass...word
✅ TENANT_ID: 1234...5678
✅ USER_ID: user@domain.com
✅ ADMIN_USER_ID: 123456789
🎉 All required environment variables are configured!
```

## Troubleshooting
If environment variable issues persist:

1. **Check Repository Secrets**: Verify all secrets are set in GitHub repository settings
2. **Run Debug Script**: Use `python debug_env.py` to identify missing variables
3. **Check Workflow Logs**: Look for the "Debug environment variables" step output
4. **Verify Secret Names**: Ensure secret names match exactly (case-sensitive)

## Prevention
- Always use the debug script when adding new environment variables
- Test workflows in a development repository before production deployment
- Use the alternative naming conventions for flexibility across different deployment environments
