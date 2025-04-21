#!/usr/bin/env python3
import os
import logging
import json
import datetime
import argparse
import subprocess
from feed_manager import FeedManager
from ebook_generator import EbookGenerator
from email_sender import EmailSender

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'daynews.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='DayNews: RSS to e-book automation')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--send-email', action='store_true', help='Send email with e-book')
    parser.add_argument('--low-memory', action='store_true', help='Use low memory settings (recommended for Raspberry Pi)')
    parser.add_argument('--max-articles', type=int, default=10, help='Maximum articles per feed')
    parser.add_argument('--timeout', type=int, default=900, help='Timeout for ebook generation in seconds')
    parser.add_argument('--debug', action='store_true', help='Show debug information')
    args = parser.parse_args()
    
    # Set more verbose logging if debug mode
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    try:
        # Display prominent test mode message
        if args.test:
            print("\n===== RUNNING IN TEST MODE =====")
            print("• Using minimal content for faster processing")
            print("• Working with a known-good feed for reliability")
            print("• Using simplified ebook-convert options")
            print("• Email will be sent in dry-run mode\n")
            logger.info("Starting DayNews process in TEST MODE")
            # Override settings for test mode
            args.max_articles = 1
            args.timeout = 300  # Shorter timeout for test mode
        else:
            logger.info("Starting DayNews process in NORMAL MODE")
        
        # Load configuration
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        
        # Ensure directories exist
        for directory in [config_dir, output_dir, logs_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Generate current date for filename
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        epub_filename = f"DayNews_{current_date}.epub"
        epub_path = os.path.join(output_dir, epub_filename)
        
        # Check if feeds config exists
        feeds_config_path = os.path.join(config_dir, 'feeds.json')
        if not os.path.isfile(feeds_config_path):
            logger.error(f"Feeds configuration file not found: {feeds_config_path}")
            raise FileNotFoundError(f"Missing configuration file: {feeds_config_path}")
        
        # Initialize components
        feed_manager = FeedManager(feeds_config_path, test_mode=args.test)
        ebook_generator = EbookGenerator()
        
        # Get feeds and create recipe file
        logger.info("Fetching feed data...")
        feeds_data = feed_manager.fetch_feeds()
        
        # Check if we have any valid feeds
        if not feeds_data['feeds']:
            logger.error("No valid feeds could be fetched")
            raise ValueError("No feeds to process - please check your feeds.json file")
        
        # Determine max_articles value to use
        max_articles_to_use = 1 if args.test else args.max_articles
        logger.info(f"Using max_articles={max_articles_to_use} for recipe generation")
        
        logger.info(f"Creating recipe file with {len(feeds_data['feeds'])} feeds...")
        recipe_path = ebook_generator.create_recipe_file(
            feeds_data, 
            output_dir, 
            max_articles=max_articles_to_use,
            test_mode=args.test
        )
        
        # Generate EPUB from recipe with proper parameters
        logger.info(f"Generating ebook with max_articles={max_articles_to_use}...")
        ebook_generator.generate_ebook(
            recipe_path=recipe_path, 
            output_path=epub_path,
            low_memory=args.low_memory,
            timeout=args.timeout,
            max_articles=max_articles_to_use,
            show_progress=True,
            test_mode=args.test
        )
        
        # Verify file was created before attempting to send
        if not os.path.isfile(epub_path):
            logger.error(f"Ebook file was not created at {epub_path}")
            raise FileNotFoundError(f"Failed to generate ebook file: {epub_path}")
            
        logger.info(f"Successfully generated ebook: {epub_path}")
        if args.test:
            print("\n===== TEST MODE COMPLETED SUCCESSFULLY =====")
            print(f"• Test ebook saved to: {epub_path}")
        
        # Send email with attachment if requested or not in test mode
        if args.send_email or (not args.test and not args.send_email):
            email_config_path = os.path.join(config_dir, 'email_config.json')
            if not os.path.isfile(email_config_path):
                logger.warning(f"Email configuration file not found: {email_config_path}")
                logger.warning("Skipping email sending.")
            else:
                logger.info("Sending email...")
                email_sender = EmailSender(email_config_path, dry_run=args.test)
                email_sender.send_email(epub_path)
        
        logger.info(f"DayNews process completed successfully. Created {epub_filename}")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}", exc_info=True)
        print(f"ERROR: {str(e)}")
        return 1
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.cmd}")
        logger.error(f"Return code: {e.returncode}")
        if e.stdout:
            logger.error(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")
        print(f"ERROR: Command failed with return code {e.returncode}")
        return 1
    except Exception as e:
        logger.error(f"Error in DayNews process: {str(e)}", exc_info=True)
        print(f"ERROR: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
