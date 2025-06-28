# Keep-Alive System for Render Free Tier

This document explains the comprehensive keep-alive system implemented to prevent your OneDrive Telegram Bot from sleeping on Render's free tier.

## Problem

Render's free tier puts services to sleep after 15 minutes of inactivity. This causes:
- Bot becomes unresponsive until first user interaction
- Long startup times (10-30 seconds)
- Poor user experience
- Potential message loss

## Solution Components

### 1. Internal Keep-Alive System (`app.py`)

**Self-Ping Mechanism:**
- Bot pings its own `/health` endpoint every 10 minutes
- Maintains activity during idle periods
- Prevents Render from detecting inactivity

**Enhanced Health Endpoints:**
- `/health` - Comprehensive health status with JSON/text format
- `/ping` - Simple ping endpoint (returns "pong")
- `/metrics` - Prometheus-style metrics for monitoring

**Features:**
```python
# Automatic self-ping every 10 minutes
await self.self_ping_health_endpoint()

# Enhanced health monitoring with detailed status
GET /health
Accept: application/json  # Returns JSON
Accept: text/plain        # Returns human-readable text
```

### 2. External Uptime Monitor (`uptime_monitor.py`)

**Standalone Script:**
- Can run independently from any service
- Pings multiple endpoints to ensure service stays alive
- Provides detailed monitoring output

**Usage:**
```bash
# Set your service URL
export WEBHOOK_URL="https://your-service.onrender.com"

# Run the monitor
python uptime_monitor.py
```

### 3. GitHub Actions Uptime Monitor (`.github/workflows/uptime-monitor.yml`)

**Automated External Monitoring:**
- Runs every 10 minutes automatically
- Uses GitHub's free Actions minutes
- No additional hosting required

**Setup:**
1. Fork/clone this repository
2. Add repository secret: `WEBHOOK_URL` = your Render service URL
3. GitHub Actions will automatically ping your service every 10 minutes

### 4. Enhanced Bot Keep-Alive (`bot.py`)

**Intelligent Keep-Alive:**
- Monitors indexing operations
- Sends progress updates during long operations
- Self-pings during critical processes

**Features:**
```python
# Start keep-alive during long operations
keepalive_task = await self.start_keepalive_during_operation("indexing")

# Enhanced ping with self-monitoring
await self.send_keepalive_ping()
```

## Configuration

### Environment Variables

```bash
# Required - Your Render service URL
WEBHOOK_URL=https://your-service.onrender.com

# Optional - External uptime monitor URL
UPTIME_MONITOR_URL=https://your-monitor-service.com/ping

# Optional - Enable debug mode for detailed logs
DEBUG=true
```

### Render Configuration

Add to your `render.yaml`:
```yaml
services:
  - type: web
    name: onedrive-telegram-bot
    healthCheckPath: /health  # Uses our enhanced health endpoint
```

## Monitoring Endpoints

### Health Check (`GET /health`)

**Human-readable format:**
```
🤖 OneDrive Telegram Bot - Health Status
==================================================

✅ Status: HEALTHY
🕐 Timestamp: 2025-01-28T10:30:00.000Z

🤖 Bot Information:
  • Username: @your_bot
  • Uptime: 2h 15m
  • Webhook: https://your-service.onrender.com/webhook

⚡ Activity (ACTIVE):
  • Last activity: 30 seconds ago

📁 Indexing (IDLE):
  • Progress: 0%

💾 Storage:
  • Database: enabled
  • Git integration: enabled

🚀 Render Configuration:
  • Port: 10000
  • Host: 0.0.0.0
  • Keep-alive: enabled
```

**JSON format (with `Accept: application/json`):**
```json
{
  "status": "healthy",
  "bot": {
    "username": "your_bot",
    "uptime_seconds": 8100,
    "uptime_human": "2h 15m"
  },
  "activity": {
    "last_activity_seconds_ago": 30,
    "status": "active"
  },
  // ... more details
}
```

### Ping Endpoint (`GET /ping`)

Simple endpoint that returns "pong" - perfect for basic uptime monitors.

### Metrics Endpoint (`GET /metrics`)

Prometheus-style metrics for advanced monitoring:
```
# HELP bot_uptime_seconds Total uptime of the bot in seconds
# TYPE bot_uptime_seconds counter
bot_uptime_seconds 8100

# HELP bot_last_activity_seconds Time since last activity in seconds
# TYPE bot_last_activity_seconds gauge
bot_last_activity_seconds 30
```

## Usage Examples

### Check Bot Status
```bash
# Simple ping
curl https://your-service.onrender.com/ping

# Detailed health check
curl https://your-service.onrender.com/health

# JSON status
curl -H "Accept: application/json" https://your-service.onrender.com/health
```

### External Monitoring Setup

**UptimeRobot:**
- Monitor Type: HTTP(s)
- URL: `https://your-service.onrender.com/ping`
- Interval: 5 minutes

**GitHub Actions (included):**
- Automatically monitors every 10 minutes
- Uses repository secrets for configuration
- No additional setup required

### Manual Monitoring Script

Create a simple cron job:
```bash
# Run every 5 minutes
*/5 * * * * /usr/bin/python3 /path/to/uptime_monitor.py
```

## Benefits

1. **99%+ Uptime:** Bot stays active continuously
2. **Fast Response:** No cold start delays for users
3. **Zero Cost:** Uses GitHub Actions free minutes
4. **Monitoring:** Comprehensive health and metrics endpoints
5. **Reliability:** Multiple redundant keep-alive mechanisms

## Troubleshooting

### Bot Still Sleeping
- Check GitHub Actions logs for uptime monitor failures
- Verify `WEBHOOK_URL` environment variable is correct
- Test health endpoint manually: `curl https://your-service.onrender.com/health`

### High Response Times
- Monitor `/metrics` endpoint for performance data
- Check Render logs for any errors or warnings
- Consider upgrading to Render paid tier for better performance

### GitHub Actions Not Running
- Check repository settings → Actions (ensure enabled)
- Verify `WEBHOOK_URL` secret is set correctly
- Check Actions tab for any failed workflow runs

## Monitoring Dashboard

You can create a simple monitoring dashboard using the metrics endpoint with tools like:
- Grafana (free tier available)
- UptimeRobot status pages
- Custom dashboard using the JSON health endpoint

The enhanced keep-alive system ensures your bot remains responsive 24/7 while maximizing the value of Render's free tier!
