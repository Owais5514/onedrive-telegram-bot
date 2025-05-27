#!/bin/bash

echo "🚀 Setting up OneDrive Telegram Bot..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please edit the .env file with your credentials:"
    echo "   - BOT_TOKEN (from @BotFather on Telegram)"
    echo "   - CLIENT_ID (from Azure App Registration)"
    echo "   - CLIENT_SECRET (from Azure App Registration)"
    echo "   - TENANT_ID (from Azure App Registration)"
    echo ""
    echo "🔍 Use 'nano .env' or your preferred editor to edit the file."
else
    echo "✅ .env file already exists."
fi

echo ""
echo "🎉 Setup complete! Next steps:"
echo "1. Edit the .env file with your credentials"
echo "2. Set up your Azure App Registration (see README.md for details)"
echo "3. Run the bot with: python bot.py"
echo ""
echo "📖 For detailed setup instructions, see README.md"
