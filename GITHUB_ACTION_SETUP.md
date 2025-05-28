# GitHub Action Setup Guide for OneDrive Telegram Bot

## 🚀 Overview
This guide will help you set up GitHub Actions to automatically run your OneDrive Telegram Bot daily at 9:00 AM Bangladesh time for 1 hour.

## ⚙️ Step 1: Push Code to GitHub

1. **Create a new GitHub repository** (if you haven't already)
2. **Push your bot code** to the repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: OneDrive Telegram Bot"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

## 🔐 Step 2: Set Up GitHub Secrets

Go to your GitHub repository and navigate to: **Settings** → **Secrets and variables** → **Actions**

Click **"New repository secret"** and add each of the following secrets:

### Required Secrets:

#### 1. **TENANT_ID**
- **Name:** `TENANT_ID`
- **Value:** Your Azure AD Tenant ID (from your .env file)
- **Example:** `12345678-1234-1234-1234-123456789abc`

#### 2. **CLIENT_ID** 
- **Name:** `CLIENT_ID`
- **Value:** Your Azure App Registration Client ID
- **Example:** `87654321-4321-4321-4321-987654321def`

#### 3. **CLIENT_SECRET**
- **Name:** `CLIENT_SECRET` 
- **Value:** Your Azure App Registration Client Secret
- **Example:** `ABC123def456GHI789jkl012MNO345pqr678STU`

#### 4. **BOT_TOKEN**
- **Name:** `BOT_TOKEN`
- **Value:** Your Telegram Bot Token (from @BotFather)
- **Example:** `1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ123456789`

#### 5. **CLAUDE_API_KEY**
- **Name:** `CLAUDE_API_KEY`
- **Value:** Your Claude AI API Key
- **Example:** `sk-ant-api03-...your-claude-key...`

### Optional Secret:

#### 6. **WEBHOOK_URL** (Optional)
- **Name:** `WEBHOOK_URL`
- **Value:** Leave empty for polling mode, or provide webhook URL if using webhooks
- **Example:** `https://your-domain.com/webhook` or leave empty

## 📋 Step 3: Copy Your Current Environment Values

To get the exact values you need, check your current `.env` file:

```bash
# In your project directory:
cat .env
```

Copy each value and paste it into the corresponding GitHub secret.

## 🕘 Step 4: Verify Schedule (Bangladesh Time)

The bot is scheduled to run:
- **Time:** 9:00 AM Bangladesh Time (UTC+6)
- **Cron Expression:** `0 3 * * *` (3:00 AM UTC = 9:00 AM Bangladesh Time)
- **Duration:** 1 hour
- **Frequency:** Daily

## ✅ Step 5: Test the Setup

### Manual Test:
1. Go to your repository on GitHub
2. Navigate to **Actions** tab
3. Click on **"OneDrive Telegram Bot Daily Run"** workflow
4. Click **"Run workflow"** → **"Run workflow"** button
5. Monitor the run to ensure it starts successfully

### Check Logs:
- Click on any workflow run to see detailed logs
- Look for success messages like "✅ All required environment variables are set"
- Bot activity will be logged during the 1-hour run

## 🔧 Step 6: Troubleshooting

### Common Issues:

1. **Missing Secrets Error:**
   ```
   ❌ TENANT_ID is missing
   ```
   **Solution:** Ensure all secrets are properly set in GitHub repository settings

2. **Authentication Failures:**
   ```
   Error: Authentication failed
   ```
   **Solution:** Verify your Azure credentials and permissions

3. **Bot Token Issues:**
   ```
   Error: Bot token invalid
   ```
   **Solution:** Check your Telegram bot token from @BotFather

### Environment Variables Checklist:
- [ ] TENANT_ID (Azure AD Tenant ID)
- [ ] CLIENT_ID (Azure App Registration Client ID)  
- [ ] CLIENT_SECRET (Azure App Registration Client Secret)
- [ ] BOT_TOKEN (Telegram Bot Token)
- [ ] CLAUDE_API_KEY (Claude AI API Key)

## 🚨 Security Notes

1. **Never commit sensitive data** to your repository
2. **Use GitHub Secrets** for all sensitive information
3. **Regular token rotation** is recommended
4. **Monitor workflow runs** for any security issues

## 📊 Monitoring

### Check Bot Status:
- **GitHub Actions Logs:** Real-time bot activity
- **Telegram:** Test bot responses during active hours
- **Artifacts:** Bot logs are saved for 7 days after each run

### Workflow Features:
- ✅ Automatic daily execution
- ✅ 1-hour runtime limit
- ✅ Manual trigger option
- ✅ Log artifacts upload
- ✅ Secure environment cleanup
- ✅ Error handling and verification

## 🎯 Next Steps

1. **Set up all GitHub secrets** using your current .env values
2. **Push the workflow file** to your repository
3. **Test with manual trigger** first
4. **Monitor the first automated run** tomorrow at 9 AM Bangladesh time

The bot will now automatically start every day at 9 AM Bangladesh time and run for exactly 1 hour, providing your users with consistent daily access to the OneDrive search functionality.
