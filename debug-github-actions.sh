#!/bin/bash

# GitHub Actions Debug Helper
# This script helps diagnose common GitHub Actions issues

echo "🔍 GitHub Actions Debug Helper"
echo "==============================="
echo ""

# Check if we're in the right directory
if [ ! -f "bot_continuous.py" ]; then
    echo "❌ Error: bot_continuous.py not found!"
    echo "Please run this script from the project root directory."
    exit 1
fi

echo "✅ Project files found"
echo ""

# Check Python version
echo "🐍 Python Version:"
python --version
echo ""

# Check if all required packages are installed
echo "📦 Checking Python packages..."
echo "Required packages:"

packages=("python-telegram-bot" "azure-identity" "azure-storage-file-share" "anthropic" "python-dotenv")
missing_packages=()

for package in "${packages[@]}"; do
    if pip show "$package" >/dev/null 2>&1; then
        version=$(pip show "$package" | grep Version | cut -d' ' -f2)
        echo "  ✅ $package ($version)"
    else
        echo "  ❌ $package (missing)"
        missing_packages+=("$package")
    fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    echo ""
    echo "🚨 Missing packages detected. Installing..."
    pip install "${missing_packages[@]}"
fi

echo ""

# Check environment variables
echo "🔐 Environment Variables Check:"
if [ -f ".env" ]; then
    echo "  ✅ .env file found"
    
    required_vars=("TELEGRAM_BOT_TOKEN" "AZURE_CLIENT_ID" "AZURE_CLIENT_SECRET" "AZURE_TENANT_ID" "CLAUDE_API_KEY")
    
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env; then
            value=$(grep "^${var}=" .env | cut -d'=' -f2)
            if [ -n "$value" ] && [ "$value" != "" ]; then
                echo "  ✅ $var (set)"
            else
                echo "  ❌ $var (empty)"
            fi
        else
            echo "  ❌ $var (missing)"
        fi
    done
else
    echo "  ❌ .env file not found"
fi

echo ""

# Test bot import
echo "🤖 Testing Bot Import:"
python -c "
try:
    import bot_continuous
    print('  ✅ Bot module imports successfully')
except ImportError as e:
    print(f'  ❌ Import error: {e}')
except Exception as e:
    print(f'  ❌ Other error: {e}')
"

echo ""

# Test basic connectivity
echo "🌐 Testing Basic Connectivity:"
echo "  Testing internet connection..."
if curl -s --connect-timeout 10 https://api.telegram.org > /dev/null; then
    echo "  ✅ Telegram API reachable"
else
    echo "  ❌ Cannot reach Telegram API"
fi

if curl -s --connect-timeout 10 https://login.microsoftonline.com > /dev/null; then
    echo "  ✅ Microsoft Azure reachable"
else
    echo "  ❌ Cannot reach Microsoft Azure"
fi

echo ""

# Check GitHub workflow
echo "📋 GitHub Workflow Check:"
if [ -f ".github/workflows/daily-bot-run.yml" ]; then
    echo "  ✅ GitHub workflow file found"
    echo "  Checking for common issues..."
    
    if grep -q "actions/upload-artifact@v3" .github/workflows/daily-bot-run.yml; then
        echo "  ⚠️  WARNING: Using deprecated actions/upload-artifact@v3"
        echo "              Should be updated to @v4"
    fi
    
    if grep -q "actions/setup-python@v4" .github/workflows/daily-bot-run.yml; then
        echo "  ✅ Python setup action version looks good"
    fi
    
else
    echo "  ❌ GitHub workflow file not found"
fi

echo ""
echo "🎯 Summary:"
echo "----------"
echo "If you see any ❌ errors above, those need to be fixed for GitHub Actions to work."
echo ""
echo "Common solutions:"
echo "• Missing packages: Run 'pip install -r requirements.txt'"
echo "• Missing .env: Copy environment variables from working setup"
echo "• Import errors: Check Python version compatibility"
echo "• Network issues: Usually resolve themselves, try again later"
echo ""
echo "For GitHub Actions specifically:"
echo "• Make sure all secrets are configured in GitHub repository settings"
echo "• Secret names must match exactly: TENANT_ID, CLIENT_ID, CLIENT_SECRET, BOT_TOKEN, CLAUDE_API_KEY"
echo "• Workflow file should use latest action versions (v4, v5)"
