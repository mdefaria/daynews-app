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
