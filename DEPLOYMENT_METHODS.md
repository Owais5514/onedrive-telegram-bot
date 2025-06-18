# Bot Deployment Methods

This bot supports multiple deployment methods to suit different use cases and environments.

## Available Methods

### 1. Polling Method (Default)
**Current implementation** - The bot continuously asks Telegram servers for new updates.

**Pros:**
- ✅ Simple setup - no additional configuration needed
- ✅ Works behind NAT/firewall
- ✅ No SSL certificate required
- ✅ Good for development and testing
- ✅ Works on any hosting environment

**Cons:**
- ❌ Less efficient (makes constant API calls)
- ❌ Higher latency for message delivery
- ❌ May hit rate limits with high traffic
- ❌ Uses more bandwidth

**Usage:**
```bash
# Current method (default)
python main.py

# Or explicitly specify polling
python main_enhanced.py polling
```

### 2. Webhook Method (Production Recommended)
**New implementation** - Telegram sends updates directly to your server.

**Pros:**
- ✅ More efficient (push notifications)
- ✅ Lower latency - instant message delivery
- ✅ Better for high-traffic bots
- ✅ Scales better
- ✅ Reduced API calls

**Cons:**
- ❌ Requires public HTTPS endpoint
- ❌ More complex setup
- ❌ Need SSL certificate
- ❌ Server must be publicly accessible

**Usage:**
```bash
python main_enhanced.py webhook
```

## Setup Instructions

### Polling Setup (Current)
1. Just run your bot as usual:
   ```bash
   python main.py
   ```
2. No additional configuration needed!

### Webhook Setup

#### Option 1: Using a Domain with Valid SSL
1. Get a domain and point it to your server
2. Set up HTTPS (using Let's Encrypt, Cloudflare, etc.)
3. Add to your `.env` file:
   ```env
   WEBHOOK_URL=https://yourdomain.com
   WEBHOOK_PATH=/webhook
   WEBHOOK_PORT=8443
   ```
4. Run the bot:
   ```bash
   python main_enhanced.py webhook
   ```

#### Option 2: Using ngrok (Development/Testing)
1. Install ngrok: https://ngrok.com/
2. Start ngrok tunnel:
   ```bash
   ngrok http 8443
   ```
3. Copy the HTTPS URL from ngrok output
4. Add to your `.env` file:
   ```env
   WEBHOOK_URL=https://your-random-id.ngrok.io
   WEBHOOK_PATH=/webhook
   WEBHOOK_PORT=8443
   ```
5. Run the bot:
   ```bash
   python main_enhanced.py webhook
   ```

#### Option 3: Self-Signed Certificate
1. Generate SSL certificate:
   ```bash
   openssl req -newkey rsa:2048 -sha256 -nodes -keyout private.key -x509 -days 365 -out public.pem
   ```
2. Add to your `.env` file:
   ```env
   WEBHOOK_URL=https://your-server-ip:8443
   WEBHOOK_PATH=/webhook
   WEBHOOK_PORT=8443
   SSL_CERT_FILE=public.pem
   SSL_KEY_FILE=private.key
   ```
3. Run the bot:
   ```bash
   python main_enhanced.py webhook
   ```

## Environment Variables

### Required for All Methods
```env
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_USER_ID=your_user_id
MICROSOFT_CLIENT_ID=your_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret
MICROSOFT_TENANT_ID=your_tenant_id
```

### Additional for Webhook Method
```env
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_PATH=/webhook
WEBHOOK_PORT=8443
WEBHOOK_HOST=0.0.0.0
SSL_CERT_FILE=path/to/cert.pem  # Optional
SSL_KEY_FILE=path/to/key.pem    # Optional
```

## Switching Between Methods

### From Polling to Webhook
1. Stop the current bot (Ctrl+C)
2. Configure webhook environment variables
3. Start with webhook:
   ```bash
   python main_enhanced.py webhook
   ```

### From Webhook to Polling
1. Stop the current bot (Ctrl+C)
2. Start with polling:
   ```bash
   python main_enhanced.py polling
   ```
The webhook will be automatically removed when switching to polling.

## Troubleshooting

### Webhook Issues
- **"Failed to set webhook"**: Check if WEBHOOK_URL is publicly accessible via HTTPS
- **"SSL certificate error"**: Ensure certificate files exist and are valid
- **"Port already in use"**: Change WEBHOOK_PORT or stop other services using the port
- **"403 Forbidden"**: Check if your server firewall allows incoming connections

### General Issues
- **"Bot token invalid"**: Verify TELEGRAM_BOT_TOKEN in .env file
- **"Admin ID not set"**: Add your Telegram user ID to ADMIN_USER_ID

## Performance Comparison

| Feature | Polling | Webhook |
|---------|---------|---------|
| Setup Complexity | Easy | Medium |
| Response Time | 1-30 seconds | Instant |
| Resource Usage | Higher | Lower |
| Scalability | Limited | Excellent |
| Reliability | Good | Excellent |
| Public IP Required | No | Yes |
| SSL Required | No | Yes |

## Recommendations

- **Development/Testing**: Use polling method
- **Personal Use**: Use polling method
- **Production/High Traffic**: Use webhook method
- **Public Deployment**: Use webhook method

## Security Considerations

### Polling
- Only requires outbound internet access
- No incoming connections needed

### Webhook
- Requires public HTTPS endpoint
- Consider using a reverse proxy (nginx, Apache)
- Implement rate limiting if needed
- Monitor for suspicious webhook requests

## Files Overview

- `main.py` - Original launcher (polling only)
- `main_enhanced.py` - Enhanced launcher (supports both methods)
- `bot.py` - Original bot implementation (polling)
- `bot_webhook.py` - Enhanced bot with webhook support
- `.env.example.enhanced` - Environment configuration template
