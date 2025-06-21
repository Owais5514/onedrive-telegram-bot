# OneDrive Telegram Bot - Render Deployment Checklist

Use this checklist to ensure a successful deployment to Render.com.

## Pre-Deployment Checklist

### 1. Repository Setup
- [ ] Code is pushed to GitHub repository
- [ ] `.env` files are **NOT** committed (check `.gitignore`)
- [ ] All required files are present:
  - [ ] `app.py` (main Render application)
  - [ ] `bot.py` (bot implementation)
  - [ ] `indexer.py` (OneDrive indexer)
  - [ ] `requirements.txt` (dependencies)
  - [ ] `render.yaml` (service configuration)
  - [ ] `Procfile` (alternative start command)
  - [ ] `runtime.txt` (Python version)

### 2. Credentials Ready
- [ ] **Telegram Bot Token** from @BotFather
- [ ] **Admin User ID** (your Telegram user ID)
- [ ] **Azure App Registration** credentials:
  - [ ] Client ID
  - [ ] Client Secret  
  - [ ] Tenant ID
- [ ] **Target User ID** (OneDrive owner)

### 3. Azure Configuration
- [ ] Azure App Registration created
- [ ] **API Permissions** granted:
  - [ ] `Files.Read.All` (Application permission)
  - [ ] `User.Read.All` (Application permission)
- [ ] **Admin consent** granted for permissions
- [ ] **Client secret** created and noted

## Render Deployment Steps

### 1. Create Render Account
- [ ] Sign up at [render.com](https://render.com)
- [ ] Connect GitHub account
- [ ] Verify email address

### 2. Create Web Service
- [ ] Click "New +" → "Web Service"
- [ ] Connect to your GitHub repository
- [ ] Configure service settings:
  - [ ] **Name**: `onedrive-telegram-bot`
  - [ ] **Region**: Choose appropriate region
  - [ ] **Branch**: `main` or your default branch
  - [ ] **Runtime**: `Python 3`
  - [ ] **Build Command**: `pip install -r requirements.txt`
  - [ ] **Start Command**: `python app.py`
  - [ ] **Plan**: `Starter` (free) or `Standard` (paid)

### 3. Configure Environment Variables
Add these in Render service → Environment tab:

#### Required Variables
- [ ] `TELEGRAM_BOT_TOKEN=your_bot_token`
- [ ] `ADMIN_USER_ID=your_telegram_user_id`
- [ ] `AZURE_CLIENT_ID=your_azure_client_id`
- [ ] `AZURE_CLIENT_SECRET=your_azure_client_secret`
- [ ] `AZURE_TENANT_ID=your_azure_tenant_id`
- [ ] `TARGET_USER_ID=your_onedrive_user_id`

#### Optional Variables
- [ ] `WEBHOOK_PATH=/webhook`
- [ ] `LOG_LEVEL=INFO`
- [ ] `PYTHON_VERSION=3.12`

### 4. Deploy Service
- [ ] Click "Create Web Service"
- [ ] Wait for initial deployment (2-5 minutes)
- [ ] Check build logs for errors
- [ ] Verify deployment success

## Post-Deployment Verification

### 1. Service Health
- [ ] Visit health endpoint: `https://your-service.onrender.com/health`
- [ ] Should show "OneDrive Telegram Bot is running"
- [ ] Check Render dashboard logs for any errors

### 2. Bot Functionality
- [ ] Start conversation with your bot on Telegram
- [ ] Send `/start` command
- [ ] Verify bot responds with welcome message
- [ ] Test basic navigation (browse folders)
- [ ] Test file download functionality

### 3. Webhook Verification
- [ ] Bot responds immediately to messages (not after delay)
- [ ] Check Render logs for webhook request processing
- [ ] No polling-related messages in logs

### 4. Admin Features
- [ ] Send `/admin` command
- [ ] Verify admin panel is accessible
- [ ] Test admin functions (if needed)

## Troubleshooting Checklist

### If Service Won't Start
- [ ] Check Render build logs for dependency issues
- [ ] Verify all environment variables are set correctly
- [ ] Ensure `app.py` is present and executable
- [ ] Check Python version compatibility

### If Bot Doesn't Respond
- [ ] Verify `TELEGRAM_BOT_TOKEN` is correct
- [ ] Check webhook URL is accessible
- [ ] Test health endpoint manually
- [ ] Review bot logs for authentication errors

### If OneDrive Access Fails
- [ ] Verify Azure credentials are correct
- [ ] Check Azure app permissions are granted
- [ ] Confirm admin consent is provided
- [ ] Test with OneDrive folder discovery tool

### If Service Keeps Restarting
- [ ] Check for memory usage issues
- [ ] Review error logs for crash causes
- [ ] Consider upgrading to higher tier plan
- [ ] Verify all dependencies are compatible

## Monitoring and Maintenance

### Regular Checks
- [ ] Monitor service uptime in Render dashboard
- [ ] Check bot responsiveness periodically
- [ ] Review logs for any errors or warnings
- [ ] Monitor resource usage

### Updates and Maintenance
- [ ] Enable auto-deploy for automatic updates
- [ ] Test new features in a separate service first
- [ ] Keep credentials secure and rotate periodically
- [ ] Monitor Azure app registration expiration

### Performance Optimization
- [ ] Consider upgrading plan for better performance
- [ ] Monitor response times and optimize if needed
- [ ] Use health checks to ensure service availability
- [ ] Set up external monitoring if required

## Security Checklist

### Credential Security
- [ ] Never commit `.env` files to repository
- [ ] Use Render environment variables for all secrets
- [ ] Rotate tokens and secrets periodically
- [ ] Limit Azure app permissions to minimum required

### Access Control
- [ ] Verify admin user ID is correct
- [ ] Test admin-only functions are properly restricted
- [ ] Monitor for unauthorized access attempts
- [ ] Keep bot token private and secure

### Network Security
- [ ] Webhook endpoint is properly secured
- [ ] Health check doesn't expose sensitive information
- [ ] Monitor for unusual traffic patterns
- [ ] Consider rate limiting if needed

## Final Verification

### Complete End-to-End Test
1. [ ] Send `/start` to bot
2. [ ] Navigate through folders
3. [ ] Download a file
4. [ ] Use admin functions (if applicable)
5. [ ] Check logs for any errors
6. [ ] Verify performance is acceptable

### Documentation
- [ ] Update any deployment documentation
- [ ] Note any configuration changes made
- [ ] Document any issues encountered and solutions
- [ ] Share access details with team members if needed

## Success Criteria

✅ **Deployment Successful When:**
- Service is running without errors
- Bot responds to Telegram messages immediately  
- File browsing and downloading works correctly
- Health endpoint returns positive status
- No critical errors in logs
- All admin functions work as expected

---

🎉 **Congratulations!** Your OneDrive Telegram Bot is now successfully deployed on Render!

**Next Steps:**
- Monitor the service for the first few days
- Consider upgrading to paid tier for production use
- Set up monitoring alerts if needed
- Enjoy your always-on OneDrive Telegram bot!
