#!/bin/bash

# Exit on error
set -e

echo "Setting up DayNews App..."

# Create necessary directories
mkdir -p logs output

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Installing..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
fi

# Install required Python packages
echo "Installing Python dependencies..."
pip3 install feedparser

# Check if Calibre is installed
if ! command -v ebook-convert &> /dev/null; then
    echo "Calibre is required but not installed. Installing..."
    sudo apt-get update
    sudo apt-get install -y calibre
fi

# Set up cron job
echo "Setting up cron job to run daily at 6 AM..."
(crontab -l 2>/dev/null || echo "") | grep -v "daynews-app/src/main.py" | \
  (cat; echo "0 6 * * * cd $(pwd) && python3 src/main.py >> logs/cron.log 2>&1") | crontab -

echo "Making scripts executable..."
chmod +x src/main.py
chmod +x setup.sh

echo "Setup complete! The app will run daily at 6 AM."
echo "To change the configuration, edit the files in the config directory."
echo "To run the app manually, execute: python3 src/main.py"
