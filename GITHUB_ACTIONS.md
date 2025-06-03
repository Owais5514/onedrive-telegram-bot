# GitHub Actions Setup Guide

This repository includes GitHub Actions workflows to run your OneDrive Telegram Bot in the cloud.

## 🚀 Quick Setup

### 1. Configure Repository Secrets

Go to your repository → Settings → Secrets and variables → Actions, and add these secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather | `6963034827:AAGBtg0IClx60JPqPLPpQMe6EiyXNYI8-nM` |
| `CLIENT_ID` | Microsoft Azure App Registration Client ID | `12345678-1234-1234-1234-123456789012` |
| `CLIENT_SECRET` | Microsoft Azure App Client Secret | `abcdefgh~123456789` |
| `TENANT_ID` | Microsoft Azure Tenant ID | `87654321-4321-4321-4321-210987654321` |
| `USER_ID` | OneDrive user ID to index | `user@university.edu` |
| `ADMIN_USER_ID` | Telegram user ID for admin access | `123456789` |

### 2. Available Workflows

## 📋 Workflow Overview

### 🤖 Manual Bot Runner (`run-bot.yml`)
**Trigger**: Manual (workflow_dispatch)

Use this to run the bot on-demand:

1. Go to Actions tab → "Run OneDrive Telegram Bot"
2. Click "Run workflow"
3. Configure options:
   - **Duration**: How long to run (default: 60 minutes)
   - **Force Refresh**: Whether to rebuild the index

**Features**:
- ✅ Manual trigger with configurable duration
- ✅ Optional force refresh of OneDrive index
- ✅ Comprehensive logging and diagnostics
- ✅ Automatic cleanup of sensitive data
- ✅ Artifact upload for troubleshooting

### ⏰ Scheduled Runner (`scheduled-bot.yml`)
**Trigger**: Scheduled (cron) + Manual

Automatically runs the bot at scheduled times:
- **9 AM UTC** daily (adjust for your timezone)
- **6 PM UTC** daily

**Features**:
- ✅ Automatic daily sessions
- ✅ Smart index updates
- ✅ Configurable duration for manual runs
- ✅ Lightweight execution

### 🧪 Test and Build (`test-build.yml`)
**Trigger**: Push to main/develop, Pull Requests, Manual

Validates code quality and functionality:

**Features**:
- ✅ Multi-Python version testing (3.11, 3.12)
- ✅ Syntax validation
- ✅ Module import testing
- ✅ Code structure analysis
- ✅ Dependency caching

## 🎯 Usage Examples

### Running the Bot Manually

```bash
# Navigate to Actions tab in GitHub
Actions → "Run OneDrive Telegram Bot" → "Run workflow"

# Configure:
Duration: 120         # Run for 2 hours
Force Refresh: true   # Rebuild index
```

### Monitoring Execution

1. **Live Logs**: Click on the running workflow to see real-time logs
2. **Artifacts**: Download log files after completion
3. **Summary**: Check the summary for execution details

### Customizing Schedule

Edit `.github/workflows/scheduled-bot.yml`:

```yaml
schedule:
  - cron: '0 6 * * *'   # 6 AM UTC
  - cron: '0 14 * * *'  # 2 PM UTC
  - cron: '0 22 * * *'  # 10 PM UTC
```

## 🔧 Advanced Configuration

### Environment Variables

You can add additional environment variables in the workflow:

```yaml
- name: Create environment file
  run: |
    echo "TELEGRAM_BOT_TOKEN=${{ secrets.TELEGRAM_BOT_TOKEN }}" >> .env
    echo "DEBUG_MODE=true" >> .env
    echo "LOG_LEVEL=INFO" >> .env
```

### Timeout Settings

Modify timeout for longer sessions:

```yaml
timeout-minutes: 240  # 4 hours
```

### Artifact Retention

Adjust log retention period:

```yaml
retention-days: 14  # Keep logs for 2 weeks
```

## 🚨 Security Best Practices

### ✅ Do's
- Store all sensitive data in GitHub Secrets
- Use workflow timeouts to prevent runaway processes
- Regularly rotate API keys and tokens
- Monitor workflow usage and costs

### ❌ Don'ts
- Never commit credentials to the repository
- Don't run workflows for excessive durations
- Avoid storing personal data in artifacts
- Don't share repository access unnecessarily

## 🔍 Troubleshooting

### Common Issues

1. **"Secret not found" error**
   - Verify all required secrets are configured
   - Check secret names match exactly (case-sensitive)

2. **"Authentication failed"**
   - Ensure Azure app permissions are correctly set
   - Verify client ID, secret, and tenant ID

3. **"Workflow timeout"**
   - Reduce the duration parameter
   - Check for infinite loops in bot code

4. **"Bot not responding"**
   - Verify Telegram bot token is valid
   - Check bot is not running elsewhere simultaneously

### Getting Help

1. Check the Actions logs for detailed error messages
2. Download artifacts to review log files locally
3. Run the `troubleshoot.py` script locally first
4. Test the bot locally before deploying to Actions

## 📊 Monitoring and Costs

### GitHub Actions Limits (Free Tier)
- **2,000 minutes/month** for private repositories
- **Unlimited** for public repositories
- Each workflow run consumes minutes based on duration

### Cost Optimization
- Use scheduled runs efficiently
- Set appropriate timeouts
- Cache dependencies to reduce setup time
- Monitor usage in repository settings

## 🔄 Updates and Maintenance

### Updating Workflows
1. Modify workflow files in `.github/workflows/`
2. Commit and push changes
3. Test with manual triggers before relying on schedules

### Keeping Dependencies Updated
- Regularly update `requirements.txt`
- Monitor security advisories for Python packages
- Test with multiple Python versions using the test workflow

This setup provides a robust, automated way to run your OneDrive Telegram Bot in the cloud with proper security and monitoring.
