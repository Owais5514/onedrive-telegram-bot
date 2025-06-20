# Archived Files

This directory contains files that are **not necessary** for running the OneDrive Telegram Bot on Render with webhook deployment, but may be useful for other deployment methods or development purposes.

## What's Archived and Why

### `alternative-deployment/`
Files for deployment methods other than Render webhook:

- **`main.py`** - Basic launcher for polling method only
- **`main_enhanced.py`** - Enhanced launcher supporting both polling and webhook methods  
- **`bot_webhook.py`** - Alternative webhook implementation (not used by Render)
- **`start_local.py`** - Local testing script for Render mode

**Why archived:** Render deployment uses `app.py` directly, which is optimized specifically for Render's webhook infrastructure.

### `development-tools/`
Tools for development and testing:

- **`discover_folders.py`** - OneDrive folder discovery tool for configuration

**Why archived:** This is a one-time setup tool used during initial configuration, not needed for runtime.

### `additional-docs/`
Documentation for other deployment methods and architecture:

- **`DEPLOYMENT_METHODS.md`** - Guide for multiple deployment methods
- **`INTERFACE_LAYOUT.md`** - Interface documentation
- **`ARCHITECTURE.md`** - Architecture documentation

**Why archived:** While informative, these docs are not essential for Render webhook deployment. The main `README.md`, `RENDER_DEPLOYMENT.md`, and `DEPLOYMENT_CHECKLIST.md` contain all necessary information.

### `runtime-files/`
Files created during bot operation:

- **`feedback_log.txt`** - Runtime feedback log (created automatically)
- **`__pycache__/`** - Python bytecode cache (created automatically)

**Why archived:** These are generated during runtime and don't need to be in the main directory.

## Essential Files for Render Webhook Deployment

The following files remain in the root directory as they are **required** for Render webhook deployment:

### Core Application
- `app.py` - Main Render web service entry point
- `bot.py` - Core bot implementation
- `indexer.py` - OneDrive file indexing
- `git_integration.py` - Git integration (used by bot.py)

### Configuration
- `requirements.txt` - Python dependencies
- `render.yaml` - Render service configuration
- `Procfile` - Process definition for Render
- `runtime.txt` - Python version specification

### Documentation
- `README.md` - Main documentation
- `RENDER_DEPLOYMENT.md` - Render deployment guide  
- `DEPLOYMENT_CHECKLIST.md` - Deployment checklist

## Restoring Archived Files

If you need any of these files for a different deployment method:

```bash
# Example: Restore polling deployment files
cp archived/alternative-deployment/main.py .
cp archived/alternative-deployment/main_enhanced.py .

# Example: Restore development tools
cp archived/development-tools/discover_folders.py .
```

## Note

The archived files are fully functional - they were moved here purely to keep the main directory clean and focused on Render webhook deployment. They can be restored at any time if needed for alternative deployment methods or development purposes.
