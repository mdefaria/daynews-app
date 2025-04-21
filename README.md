# DayNews: RSS to E-book Automation

This application uses Calibre's command-line tools to convert RSS feeds into an e-book (EPUB) format and send it to your e-reader via email. Designed to run on a Raspberry Pi.

## Setup

1. Clone this repository to your Raspberry Pi
2. Run the setup script:
   ```
   ./setup.sh
   ```
3. Configure your feeds in `config/feeds.json`
4. Configure your email settings in `config/email_config.json`

## Email Configuration

For Gmail users, you'll need to:
1. Enable 2-factor authentication
2. Create an App Password
3. Use this App Password in `email_config.json`

## Testing

Before deploying to your Raspberry Pi, you can verify that everything works correctly:

```
# Run minimal test setup (just create directories and make scripts executable)
./test_setup.sh

# Run the tests
./test.sh
```

The test script will:
1. Run unit tests with mocked dependencies (no need for Calibre to be installed)
2. If Calibre is installed, run an integration test which:
   - Fetches articles from your configured RSS feeds
   - Generates an EPUB file
   - Simulates sending an email (without actually sending it)

If Calibre is not installed, only the unit tests will run. To run a full test with e-book generation:
```
# On macOS:
brew install calibre

# After installation:
./test.sh
```

## Manual Run

To run the application manually:
```
python3 src/main.py
```

To run with email sending:
```
python3 src/main.py --send-email
```

## Automatic Schedule

By default, the setup creates a cron job that runs daily at 6 AM. To modify the schedule:
```
crontab -e
```

**Note:** Cron jobs are automatically maintained across Raspberry Pi reboots. Once set up, the scheduled task will continue to run even after the device restarts - no need to keep it continuously powered on.

## Directory Structure

- `config/`: Configuration files
- `src/`: Python source code
- `output/`: Generated e-books
- `logs/`: Application logs
- `tests/`: Test scripts
