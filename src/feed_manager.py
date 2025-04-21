import json
import logging
import feedparser
from typing import List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class FeedManager:
    def __init__(self, feeds_config_path: str, test_mode: bool = False):
        self.feeds_config_path = feeds_config_path
        self.test_mode = test_mode
        self.feeds = self._load_feeds()
        
        if self.test_mode:
            logger.info("Feed Manager initialized in TEST MODE (processing only first feed)")
        
    def _load_feeds(self) -> List[Dict[str, Any]]:
        """Load feed configuration from JSON file."""
        try:
            with open(self.feeds_config_path, 'r') as f:
                config = json.load(f)
                
                # Check if it's a list or if it has a 'feeds' key
                if isinstance(config, list):
                    return config
                elif isinstance(config, dict) and 'feeds' in config:
                    return config['feeds']
                else:
                    logger.error("Invalid feeds configuration format.")
                    return []
        except json.JSONDecodeError:
            logger.error("Invalid JSON in feeds configuration file.")
            return []
        except Exception as e:
            logger.error(f"Error loading feeds config: {str(e)}")
            return []
    
    def fetch_feeds(self) -> Dict[str, Any]:
        """Fetch all RSS feeds and return structured data for recipe creation."""
        feeds_data = {
            'title': 'DayNews Daily Digest',
            'feeds': []
        }
        
        # In test mode, only process the first feed
        process_feeds = self.feeds[:1] if self.test_mode else self.feeds
        
        if self.test_mode:
            logger.info(f"TEST MODE: Processing only 1 feed instead of {len(self.feeds)}")
            
        successful_feeds = 0
        
        for feed in process_feeds:
            try:
                if 'url' not in feed or not feed['url']:
                    logger.warning(f"Skipping feed without URL: {feed.get('name', 'Unnamed')}")
                    continue
                
                # Validate URL format
                try:
                    parsed_url = urlparse(feed['url'])
                    if not parsed_url.scheme or not parsed_url.netloc:
                        logger.warning(f"Invalid feed URL format: {feed['url']}")
                        continue
                except Exception:
                    logger.warning(f"Invalid feed URL: {feed['url']}")
                    continue
                
                feed_name = feed.get('name', 'Unnamed Feed')
                logger.info(f"Fetching feed: {feed_name} from {feed['url']}")
                
                parsed_feed = feedparser.parse(feed['url'])
                
                # Check if the feed was successfully parsed
                if hasattr(parsed_feed, 'bozo_exception') and parsed_feed.bozo_exception:
                    logger.warning(f"Error parsing feed {feed_name}: {parsed_feed.bozo_exception}")
                
                # Check if there are any entries
                if not parsed_feed.entries:
                    logger.warning(f"No entries found in feed: {feed_name}")
                    continue
                
                # Create feed entry that matches the format expected by ebook_generator
                feed_entry = {
                    'title': feed_name,
                    'url': feed['url']
                }
                
                feeds_data['feeds'].append(feed_entry)
                successful_feeds += 1
                logger.info(f"Successfully processed feed: {feed_name}")
                
            except Exception as e:
                logger.error(f"Error fetching feed {feed.get('name', 'Unknown')}: {str(e)}")
        
        logger.info(f"Processed {successful_feeds} feeds successfully {'(TEST MODE - limited to 1 feed)' if self.test_mode else ''}")
        return feeds_data
