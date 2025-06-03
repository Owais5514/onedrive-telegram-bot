# GitHub Actions Workflows Summary

## 📋 Available Workflows

### 1. 🤖 Manual Bot Runner (`run-bot.yml`)
**Purpose**: Run the bot on-demand with full control and monitoring

**Trigger**: Manual (workflow_dispatch)

**Features**:
- ✅ Configurable runtime (default: 60 minutes)
- ✅ Optional force refresh of OneDrive index
- ✅ Comprehensive diagnostics and testing
- ✅ Artifact collection for troubleshooting
- ✅ Graceful shutdown with status reporting
- ✅ Automatic cleanup of sensitive data

**Usage**:
```
Actions → "Run OneDrive Telegram Bot" → "Run workflow"
├── Duration: 60 (minutes)
└── Force Refresh: false
```

### 2. ⏰ Scheduled Bot Runner (`scheduled-bot.yml`)
**Purpose**: Automatic daily bot sessions

**Trigger**: Scheduled cron + Manual

**Schedule**:
- 9:00 AM UTC daily
- 6:00 PM UTC daily

**Features**:
- ✅ Lightweight execution
- ✅ Smart index updates
- ✅ Configurable duration for manual runs
- ✅ Automatic cleanup

**Customization**:
Edit the cron schedule in the workflow file to match your timezone.

### 3. 🧪 Test and Build (`test-build.yml`)
**Purpose**: Continuous integration and code validation

**Trigger**: Push to main/develop, Pull Requests, Manual

**Features**:
- ✅ Multi-Python version testing (3.11, 3.12)
- ✅ Syntax validation and import testing
- ✅ Dependency caching for faster builds
- ✅ Code structure analysis
- ✅ Automated troubleshooting

## 🔧 Technical Implementation

### Graceful Shutdown System
- Uses `github_runner.py` for controlled execution
- Handles SIGTERM and SIGINT signals properly
- Automatic timeout with configurable duration
- Status reporting every 10 minutes
- Clean resource cleanup

### Security Features
- All credentials stored in GitHub Secrets
- Automatic cleanup of sensitive files
- No credentials in logs or artifacts
- Secure environment variable handling

### Monitoring and Debugging
- Real-time execution logs
- Artifact collection for troubleshooting
- Comprehensive diagnostics
- Status summaries with execution details

## 📊 Resource Usage

### GitHub Actions Limits
- **Free Tier**: 2,000 minutes/month (private repos)
- **Public Repos**: Unlimited minutes
- **Concurrent Jobs**: Up to 20 for free accounts

### Optimization
- Dependency caching reduces setup time
- Lightweight scheduled runs
- Configurable timeouts prevent waste
- Efficient artifact management

## 🚀 Quick Start

1. **Fork the repository**
2. **Add secrets** (see GITHUB_ACTIONS.md)
3. **Run manually**:
   - Go to Actions tab
   - Select "Run OneDrive Telegram Bot"
   - Click "Run workflow"
   - Configure duration and options
4. **Monitor execution** in real-time
5. **Download logs** if needed

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Secret not found" | Verify all secrets are configured correctly |
| "Permission denied" | Check Azure app permissions and consent |
| "Timeout" | Reduce duration or check for infinite loops |
| "Import error" | Verify requirements.txt and dependencies |

### Debug Steps
1. Check workflow logs for specific errors
2. Run the test workflow to validate setup
3. Download artifacts to review detailed logs
4. Test locally with same environment variables

## 📈 Monitoring Best Practices

1. **Set appropriate timeouts** based on usage patterns
2. **Monitor GitHub Actions usage** in repository settings
3. **Review logs regularly** for errors or issues
4. **Update dependencies** when security advisories are published
5. **Test workflows** after any code changes

This GitHub Actions setup provides a robust, automated way to run your OneDrive Telegram Bot in the cloud with proper monitoring, security, and resource management.
