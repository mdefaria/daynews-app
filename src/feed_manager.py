import json
import logging
import feedparser
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class FeedManager:
    def __init__(self, feeds_config_path: str):
        self.feeds_config_path = feeds_config_path
        self.feeds = self._load_feeds()
        
    def _load_feeds(self) -> List[Dict[str, Any]]:
        """Load feed configuration from JSON file."""
        try:
            with open(self.feeds_config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading feeds config: {str(e)}")
            return []
    
    def fetch_feeds(self) -> Dict[str, Any]:
        """Fetch all RSS feeds and return structured data for recipe creation."""
        feeds_data = {
            'title': 'DayNews Daily Digest',
            'feeds': []
        }
        
        for feed in self.feeds:
            try:
                logger.info(f"Fetching feed: {feed['name']} from {feed['url']}")
                parsed_feed = feedparser.parse(feed['url'])
                
                feed_info = {
                    'title': feed['name'],
                    'url': feed['url'],
                    'articles': []
                }
                
                for entry in parsed_feed.entries[:feed.get('max_articles', 10)]:
                    article = {
                        'title': entry.title,
                        'url': entry.link,
                        'summary': entry.get('summary', ''),
                        'published': entry.get('published', '')
                    }
                    feed_info['articles'].append(article)
                
                feeds_data['feeds'].append(feed_info)
                logger.info(f"Successfully fetched {len(feed_info['articles'])} articles from {feed['name']}")
                
            except Exception as e:
                logger.error(f"Error fetching feed {feed['name']}: {str(e)}")
        
        return feeds_data
