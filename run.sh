#!/bin/bash

# Sahayak Backend Run Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Sahayak Backend${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${RED}📝 Please update .env file with your actual configuration${NC}"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}📚 Installing dependencies...${NC}"
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=development
export FLASK_APP=main.py

# Run the application
echo -e "${GREEN}🎯 Starting Flask application...${NC}"
python main.py
