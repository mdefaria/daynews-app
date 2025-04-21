#!/bin/bash

echo "Setting up DayNews App for testing..."

# Create necessary directories
mkdir -p logs output

# Install required Python packages
echo "Installing Python dependencies..."
pip3 install feedparser

# Check if Calibre is installed
if ! command -v ebook-convert &> /dev/null; then
    echo "Calibre is required but not installed."
    echo "Please install Calibre from https://calibre-ebook.com/download"
    echo "Make sure the command-line tools are in your PATH."
    exit 1
fi

echo "Making scripts executable..."
chmod +x src/main.py
chmod +x test.sh

echo "Test setup complete!"
echo "To run tests: ./test.sh"
