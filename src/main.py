#!/usr/bin/env python3
import os
import logging
import json
import datetime
import argparse
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
    parser.add_argument('--timeout', type=int, default=600, help='Timeout for ebook generation in seconds')
    args = parser.parse_args()
    
    try:
        logger.info("Starting DayNews process")
        
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
        feed_manager = FeedManager(feeds_config_path)
        ebook_generator = EbookGenerator()
        
        # Get feeds and create recipe file
        logger.info("Fetching feed data...")
        feeds_data = feed_manager.fetch_feeds()
        
        # Check if we have any valid feeds
        if not feeds_data['feeds']:
            logger.error("No valid feeds could be fetched")
            raise ValueError("No feeds to process - please check your feeds.json file")
        
        logger.info(f"Creating recipe file with {len(feeds_data['feeds'])} feeds...")
        recipe_path = ebook_generator.create_recipe_file(feeds_data, output_dir)
        
        # Generate EPUB from recipe with proper parameters
        logger.info("Generating ebook...")
        ebook_generator.generate_ebook(
            recipe_path=recipe_path, 
            output_path=epub_path,
            low_memory=args.low_memory,
            timeout=args.timeout,
            max_articles=args.max_articles,
            show_progress=True  # Always show progress for better visibility
        )
        
        # Verify file was created before attempting to send
        if not os.path.isfile(epub_path):
            logger.error(f"Ebook file was not created at {epub_path}")
            raise FileNotFoundError(f"Failed to generate ebook file: {epub_path}")
            
        logger.info(f"Successfully generated ebook: {epub_path}")
        
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
    except Exception as e:
        logger.error(f"Error in DayNews process: {str(e)}", exc_info=True)
        print(f"ERROR: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
