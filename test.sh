#!/bin/bash

echo "==============================================="
echo "Running DayNews test..."
echo "==============================================="

# Create logs directory if it doesn't exist
mkdir -p logs output

# Make sure the script is executable
chmod +x src/main.py

# First run unit tests that don't require Calibre
echo "Running unit tests (with mocked Calibre dependencies)..."
python3 -m unittest tests/test_components.py

if [ $? -eq 0 ]; then
    echo "✅ Unit tests passed successfully!"
else
    echo "❌ Unit tests failed! Fix the issues before continuing."
    exit 1
fi

# Check if Calibre is installed for integration test
if ! command -v ebook-convert &> /dev/null; then
    echo "⚠️  Warning: Calibre command-line tools are not installed."
    echo "   Integration tests will be skipped."
    echo "   To run a full test, install Calibre first."
    exit 0
fi

# Run the application in test mode (integration test)
echo "Running integration test with --test flag..."
python3 src/main.py --test

# Check exit status
if [ $? -eq 0 ]; then
    echo "==============================================="
    echo "✅ Test completed successfully!"
    echo "   - Check the logs/daynews.log file for details"
    echo "   - Check the output directory for the generated e-book"
    echo "   - No email was sent (dry run)"
    echo "==============================================="
    echo ""
    echo "To run with actual email sending, use:"
    echo "python3 src/main.py --send-email"
    echo ""
else
    echo "==============================================="
    echo "❌ Integration test failed! Check the logs/daynews.log file for errors."
    echo "==============================================="
fi
