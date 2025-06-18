# OneDrive Telegram Bot - Render Deployment Guide

This guide walks you through deploying the OneDrive Telegram Bot on Render.com as a web service with webhooks.

## Why Render?

- ✅ **Free tier available** - Perfect for personal use
- ✅ **Automatic HTTPS** - No SSL certificate setup needed
- ✅ **Easy deployment** - Deploy directly from GitHub
- ✅ **Zero-downtime deployments** - Automatic updates
- ✅ **Built-in health checks** - Monitors your bot automatically
- ✅ **Environment variables** - Secure credential management

## Prerequisites

1. **Telegram Bot Token**: Get from [@BotFather](https://t.me/BotFather)
2. **Azure App Registration**: For OneDrive access (see main README.md)
3. **GitHub Account**: To connect your repository
4. **Render Account**: Sign up at [render.com](https://render.com) (free)

## Step-by-Step Deployment

### 1. Prepare Your Repository

1. **Fork or clone** this repository to your GitHub account
2. **Do not commit** your `.env` file (it should be in `.gitignore`)
3. **Push your code** to your GitHub repository

### 2. Create Render Web Service

1. **Log in** to [Render Dashboard](https://dashboard.render.com)
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository**
4. **Configure the service**:
   - **Name**: `onedrive-telegram-bot` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Plan**: `Starter` (free) or `Standard` (paid, more reliable)

### 3. Configure Environment Variables

In your Render service dashboard, go to **Environment** tab and add these variables:

#### Required Variables
```
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_ID=your_telegram_user_id
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=your_azure_tenant_id
TARGET_USER_ID=your_onedrive_user_id
```

#### Optional Variables
```
WEBHOOK_PATH=/webhook
LOG_LEVEL=INFO
PYTHON_VERSION=3.12
```

### 4. Deploy the Service

1. **Click "Create Web Service"**
2. **Wait for deployment** (usually 2-5 minutes)
3. **Check the logs** for any errors
4. **Visit the health check** at `https://your-service-name.onrender.com/health`

### 5. Verify Deployment

1. **Test the health endpoint**: Should show "OneDrive Telegram Bot is running"
2. **Check your bot on Telegram**: Send `/start` to your bot
3. **Monitor the logs** in Render dashboard for any issues

## Service URLs

After deployment, your service will be available at:
- **Main URL**: `https://your-service-name.onrender.com`
- **Health Check**: `https://your-service-name.onrender.com/health`
- **Webhook URL**: `https://your-service-name.onrender.com/webhook`

## Monitoring and Maintenance

### Health Checks
Render automatically monitors your service using the `/health` endpoint. If it fails, Render will restart your service.

### Logs
View real-time logs in the Render dashboard under the "Logs" tab.

### Auto-Deploy
Enable auto-deploy in your service settings to automatically deploy when you push to your GitHub repository.

### Scaling
- **Free tier**: Limited to 750 hours/month, sleeps after 15 minutes of inactivity
- **Paid tier**: Always-on, better performance, custom domains

## Troubleshooting

### Common Issues

#### 1. Service Won't Start
**Check logs for**:
- Missing environment variables
- Python dependency issues
- Port binding problems

**Solutions**:
- Verify all required environment variables are set
- Check `requirements.txt` for correct dependencies
- Ensure `app.py` is present and executable

#### 2. Bot Not Responding
**Check**:
- Telegram bot token is correct
- Webhook URL is accessible
- Health check endpoint works

**Solutions**:
- Test webhook URL manually: `curl https://your-service.onrender.com/health`
- Check Telegram webhook status: Use Telegram Bot API
- Review bot logs for errors

#### 3. OneDrive Connection Issues
**Check**:
- Azure credentials are correct
- Target user ID is valid
- Microsoft Graph API permissions

**Solutions**:
- Test credentials using the indexer directly
- Verify Azure app registration settings
- Check OneDrive folder permissions

#### 4. Service Sleeping (Free Tier)
**Issue**: Free tier services sleep after 15 minutes of inactivity

**Solutions**:
- Upgrade to paid tier for always-on service
- Use an external service to ping your health endpoint periodically
- Accept the limitation for personal use

### Debug Commands

Test your deployment:
```bash
# Test health endpoint
curl https://your-service-name.onrender.com/health

# Test webhook endpoint (should return "OK")
curl -X POST https://your-service-name.onrender.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather | `123456:ABC-DEF...` |
| `ADMIN_USER_ID` | Yes | Your Telegram user ID | `123456789` |
| `AZURE_CLIENT_ID` | Yes | Azure app client ID | `12345678-1234-...` |
| `AZURE_CLIENT_SECRET` | Yes | Azure app client secret | `abc123def456...` |
| `AZURE_TENANT_ID` | Yes | Azure tenant ID | `87654321-4321-...` |
| `TARGET_USER_ID` | Yes | OneDrive user ID | `user@example.com` |
| `WEBHOOK_PATH` | No | Webhook endpoint path | `/webhook` |
| `LOG_LEVEL` | No | Logging level | `INFO` |

## Cost Estimation

### Free Tier
- **Cost**: $0/month
- **Limitations**: 
  - 750 hours/month
  - Sleeps after 15 minutes
  - 512MB RAM
  - 0.1 CPU

### Starter Plan
- **Cost**: $7/month
- **Benefits**:
  - Always-on
  - 512MB RAM
  - 0.5 CPU
  - Custom domains

### Standard Plan
- **Cost**: $25/month
- **Benefits**:
  - 2GB RAM
  - 1 CPU
  - Better performance

## Security Best Practices

1. **Never commit secrets**: Use environment variables only
2. **Rotate tokens regularly**: Update bot tokens and Azure credentials
3. **Monitor access logs**: Check for unusual activity
4. **Use least privilege**: Only grant necessary permissions
5. **Enable auto-deploy**: Keep your service updated

## Support and Resources

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Render Community**: [community.render.com](https://community.render.com)
- **Bot Issues**: Create an issue in this repository
- **Render Support**: Available for paid plans

## Next Steps

After successful deployment:

1. **Test all bot features** thoroughly
2. **Set up monitoring** alerts (if needed)
3. **Configure auto-deploy** for easy updates
4. **Consider upgrading** to paid tier for production use
5. **Add custom domain** (paid tier only)

## Migration from Other Platforms

### From Heroku
- Export environment variables from Heroku
- Import them into Render
- Update any Heroku-specific configurations

### From Railway
- Similar process to Heroku
- Check for any Railway-specific environment variables

### From Self-Hosted
- Ensure all environment variables are captured
- Test webhook functionality
- Update any hardcoded domains/IPs

---

🎉 **Congratulations!** Your OneDrive Telegram Bot is now running on Render with webhook support!
