#!/bin/bash

# GitHub Secrets Setup Helper Script
# This script helps you extract values from your .env file to set up GitHub secrets

echo "🔐 GitHub Secrets Setup Helper"
echo "=================================="
echo ""

if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please make sure you're in the project directory with a .env file."
    exit 1
fi

echo "📋 Your current environment values:"
echo ""

# Function to safely extract and display env values
show_env_var() {
    local var_name=$1
    local value=$(grep "^${var_name}=" .env 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    
    if [ -n "$value" ]; then
        echo "✅ $var_name:"
        echo "   Value: $value"
        echo ""
    else
        echo "❌ $var_name: NOT FOUND"
        echo ""
    fi
}

echo "Copy these values to your GitHub repository secrets:"
echo "Go to: Settings → Secrets and variables → Actions → New repository secret"
echo ""

show_env_var "TENANT_ID"
show_env_var "CLIENT_ID" 
show_env_var "CLIENT_SECRET"
show_env_var "BOT_TOKEN"
show_env_var "CLAUDE_API_KEY"
show_env_var "WEBHOOK_URL"

echo "📝 GitHub Secrets to Create:"
echo "1. Secret name: TENANT_ID"
echo "2. Secret name: CLIENT_ID"
echo "3. Secret name: CLIENT_SECRET" 
echo "4. Secret name: BOT_TOKEN"
echo "5. Secret name: CLAUDE_API_KEY"
echo "6. Secret name: WEBHOOK_URL (optional - can be empty)"
echo ""

echo "⏰ Schedule Information:"
echo "• Bot will run daily at 9:00 AM Bangladesh Time"
echo "• Duration: 1 hour"
echo "• Cron: '0 3 * * *' (3 AM UTC = 9 AM Bangladesh Time)"
echo ""

echo "🚀 Next Steps:"
echo "1. Push your code to GitHub"
echo "2. Set up the secrets using the values above"
echo "3. The workflow will automatically run daily"
echo "4. You can also trigger it manually from the Actions tab"
echo ""

echo "📖 For detailed setup instructions, see: GITHUB_ACTION_SETUP.md"
