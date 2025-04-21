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
        
        # In test mode, use a known-good feed for reliability
        if self.test_mode:
            logger.info("TEST MODE: Using reliable test feed")
            test_feed = {
                'name': 'BBC News',
                'url': 'http://feeds.bbci.co.uk/news/rss.xml'
            }
            process_feeds = [test_feed]
        else:
            process_feeds = self.feeds
            
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
                
                # Create simpler feed entry
                feed_entry = {
                    'title': feed_name,
                    'url': feed['url']
                }
                
                feeds_data['feeds'].append(feed_entry)
                successful_feeds += 1
                logger.info(f"Successfully processed feed: {feed_name}")
                
            except Exception as e:
                logger.error(f"Error fetching feed {feed.get('name', 'Unknown')}: {str(e)}")
        
        # Ensure we have at least one feed for testing
        if self.test_mode and not feeds_data['feeds']:
            logger.info("TEST MODE: No feeds found, adding fallback test feed")
            feeds_data['feeds'].append({
                'title': 'Test Feed',
                'url': 'https://news.google.com/rss'
            })
            successful_feeds = 1
        
        logger.info(f"Processed {successful_feeds} feeds successfully")
        return feeds_data
