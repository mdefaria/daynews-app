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

# Check if pip3 is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 could not be found, installing..."
    sudo apt update
    sudo apt install python3-pip -y
    echo "pip3 installed successfully."
else
    echo "pip3 is already installed."
fi

# Install required Python packages
echo "Installing Python dependencies..."
# Try using apt first (preferred method)
if sudo apt-get install -y python3-feedparser; then
    echo "Installed feedparser via apt"
else
    echo "Could not install via apt, trying pip installation..."
    
    # Create a virtual environment if needed
    if [ ! -d "venv" ]; then
        echo "Creating a Python virtual environment..."
        sudo apt-get install -y python3-venv
        python3 -m venv venv
    fi
    
    echo "Installing packages in the virtual environment..."
    source venv/bin/activate
    pip3 install feedparser psutil
    deactivate
    
    echo "Note: To run the app, you'll need to activate the environment first with:"
    echo "source venv/bin/activate"
    
    # Update cron job to use the virtual environment
    VENV_PATH="$(pwd)/venv"
    (crontab -l 2>/dev/null || echo "") | grep -v "daynews-app/src/main.py" | \
      (cat; echo "0 6 * * * cd $(pwd) && $VENV_PATH/bin/python3 src/main.py >> logs/cron.log 2>&1") | crontab -
fi

# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
# Monitor ebook generation progress

# Check if app is running
if pgrep -f "python3 src/main.py" > /dev/null; then
  echo "DayNews app is currently running."
  
  # Show recent log entries
  echo -e "\nRecent log activity:"
  tail -n 20 logs/cron.log
  
  # Check for Calibre ebook-convert process
  if pgrep -f "ebook-convert" > /dev/null; then
    echo -e "\nEbook conversion is active. Current CPU/memory usage:"
    ps -o pid,%cpu,%mem,cmd -p $(pgrep -f "ebook-convert")
    
    # Show any recent output files that indicate progress
    echo -e "\nRecently modified files in output directory:"
    find output -type f -mmin -60 | sort
  else
    echo -e "\nNo active ebook conversion process found."
  fi
  
  echo -e "\nTo watch the logs in real-time, use: tail -f logs/cron.log"
else
  echo "DayNews app is not currently running."
fi
EOF

chmod +x monitor.sh

# Check if Calibre is installed - use headless version for Raspberry Pi
if ! command -v ebook-convert &> /dev/null; then
    echo "Calibre tools are required but not installed."
    echo "Installing calibre-headless (command-line tools only)..."
    sudo apt-get update
    
    # Try to install calibre-headless (much smaller package)
    if sudo apt-get install -y calibre-headless; then
        echo "Calibre command-line tools installed successfully."
    else
        echo "Could not install calibre-headless. Trying full calibre..."
        echo "Note: This may take a while on Raspberry Pi."
        
        # Ask if user wants to proceed with full install or manual install
        read -p "Install full Calibre package? (y/n, n will show manual install instructions): " choice
        if [[ "$choice" =~ ^[Yy]$ ]]; then
            sudo apt-get install -y calibre
        else
            echo ""
            echo "=== Manual Calibre CLI Tools Installation ==="
            echo "Run these commands to install Calibre CLI tools:"
            echo "1. wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sudo sh /dev/stdin install_cli"
            echo "2. After installation, run this setup script again"
            echo ""
            exit 1
        fi
    fi
fi

# Set up cron job (only if we didn't create a virtual environment)
if [ ! -d "venv" ]; then
    echo "Setting up cron job to run daily at 6 AM..."
    (crontab -l 2>/dev/null || echo "") | grep -v "daynews-app/src/main.py" | \
      (cat; echo "0 6 * * * cd $(pwd) && python3 src/main.py >> logs/cron.log 2>&1") | crontab -
fi

echo "Making scripts executable..."
chmod +x src/main.py
chmod +x setup.sh

echo "Setup complete! The app will run daily at 6 AM."
echo "To change the configuration, edit the files in the config directory."
if [ -d "venv" ]; then
    echo "To run the app manually, execute: source venv/bin/activate && python3 src/main.py"
else
    echo "To run the app manually, execute: python3 src/main.py"
fi
