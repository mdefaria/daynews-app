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
    args = parser.parse_args()
    
    try:
        logger.info("Starting DayNews process")
        
        # Load configuration
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate current date for filename
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        epub_filename = f"DayNews_{current_date}.epub"
        epub_path = os.path.join(output_dir, epub_filename)
        
        # Initialize components
        feed_manager = FeedManager(os.path.join(config_dir, 'feeds.json'))
        ebook_generator = EbookGenerator()
        email_sender = EmailSender(os.path.join(config_dir, 'email_config.json'), dry_run=args.test)
        
        # Get feeds and create recipe file
        feeds_data = feed_manager.fetch_feeds()
        recipe_path = ebook_generator.create_recipe_file(feeds_data, output_dir)
        
        # Generate EPUB from recipe
        ebook_generator.generate_ebook(recipe_path, epub_path)
        
        # Send email with attachment if requested or not in test mode
        if args.send_email or (not args.test and not args.send_email):
            email_sender.send_email(epub_path)
        
        logger.info(f"DayNews process completed successfully. Created {epub_filename}")
        
    except Exception as e:
        logger.error(f"Error in DayNews process: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
