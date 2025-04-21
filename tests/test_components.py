#!/usr/bin/env python3
import os
import sys
import unittest
import tempfile
import json
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock calibre tools before importing modules that use them
with patch('subprocess.run'):
    from src.feed_manager import FeedManager
    from src.ebook_generator import EbookGenerator
    from src.email_sender import EmailSender

class TestFeedManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary feeds.json file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.feeds_path = os.path.join(self.temp_dir.name, 'feeds.json')
        
        # Sample feeds data for testing
        self.sample_feeds = [
            {
                "name": "Test Feed 1",
                "url": "http://example.com/feed1.xml",
                "max_articles": 5
            },
            {
                "name": "Test Feed 2",
                "url": "http://example.com/feed2.xml",
                "max_articles": 3
            }
        ]
        
        with open(self.feeds_path, 'w') as f:
            json.dump(self.sample_feeds, f)
            
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def test_load_feeds(self):
        """Test that feeds are loaded correctly from config"""
        fm = FeedManager(self.feeds_path)
        self.assertEqual(len(fm.feeds), 2)
        self.assertEqual(fm.feeds[0]['name'], "Test Feed 1")
        self.assertEqual(fm.feeds[1]['url'], "http://example.com/feed2.xml")
        
    @patch('src.feed_manager.feedparser.parse')
    def test_fetch_feeds(self, mock_parse):
        """Test fetching feeds with mocked feedparser"""
        # Create mock data for feedparser response
        mock_entry = MagicMock()
        mock_entry.title = "Test Article"
        mock_entry.link = "http://example.com/article1"
        mock_entry.summary = "This is a test article"
        mock_entry.published = "Mon, 01 Jan 2023 12:00:00 GMT"
        
        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        
        # Set up the mock to return our fake feed
        mock_parse.return_value = mock_feed
        
        # Run the test
        fm = FeedManager(self.feeds_path)
        result = fm.fetch_feeds()
        
        # Verify results
        self.assertEqual(result['title'], 'DayNews Daily Digest')
        self.assertEqual(len(result['feeds']), 2)
        # The mock will return the same feed for both URLs, so we should have entries in both feeds
        self.assertEqual(len(result['feeds'][0]['articles']), 1)
        self.assertEqual(result['feeds'][0]['articles'][0]['title'], "Test Article")
        

@patch('subprocess.run')
class TestEbookGenerator(unittest.TestCase):
    def setUp(self):
        # Mock data for testing
        self.feeds_data = {
            'title': 'Test Digest',
            'feeds': [
                {
                    'title': 'Test Feed 1',
                    'url': 'http://example.com/feed1.xml',
                    'articles': []
                }
            ]
        }
        
        # Create temporary directory for output
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.temp_dir.cleanup()
    
    def test_verify_calibre_installed(self, mock_run):
        """Test verification of Calibre installation"""
        # Mock the subprocess call to simulate Calibre being installed
        mock_run.return_value = MagicMock()
        
        # This should not raise an exception
        generator = EbookGenerator()
        
        # Verify the mock was called correctly
        mock_run.assert_called()
        args, kwargs = mock_run.call_args_list[0]
        self.assertEqual(args[0][0], 'ebook-convert')
        
    def test_create_recipe_file(self, mock_run):
        """Test creation of Calibre recipe file"""
        # Mock the subprocess call to simulate Calibre being installed
        mock_run.return_value = MagicMock()
        
        # Create a recipe file
        generator = EbookGenerator()
        recipe_path = generator.create_recipe_file(self.feeds_data, self.temp_dir.name)
        
        # Verify the file was created
        self.assertTrue(os.path.exists(recipe_path))
        
        # Check the content of the file
        with open(recipe_path, 'r') as f:
            content = f.read()
            self.assertIn("title = 'Test Digest'", content)
            self.assertIn("('Test Feed 1', 'http://example.com/feed1.xml')", content)

    def test_generate_ebook(self, mock_run):
        """Test generating ebook from recipe"""
        # Mock the subprocess call
        mock_run.return_value = MagicMock(stdout="Conversion successful", stderr="")
        
        # Create generator and recipe file
        generator = EbookGenerator()
        recipe_path = generator.create_recipe_file(self.feeds_data, self.temp_dir.name)
        output_path = os.path.join(self.temp_dir.name, "test.epub")
        
        # Generate the ebook
        result = generator.generate_ebook(recipe_path, output_path)
        
        # Verify the call to ebook-convert
        mock_run.assert_called()
        args, kwargs = mock_run.call_args_list[-1]
        self.assertEqual(args[0][0], 'ebook-convert')
        self.assertEqual(args[0][1], recipe_path)
        self.assertEqual(args[0][2], output_path)
        
        # Verify the result is the output path
        self.assertEqual(result, output_path)


class TestEmailSender(unittest.TestCase):
    def setUp(self):
        # Create a temporary email_config.json file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, 'email_config.json')
        
        # Sample email config for testing
        self.sample_config = {
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "username": "test@example.com",
            "password": "testpassword",
            "from_email": "test@example.com",
            "to_email": "recipient@example.com",
            "subject": "Test Subject",
            "message_body": "Test message body",
            "use_tls": True
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.sample_config, f)
            
        # Create a temporary file to use as attachment
        self.attachment_file = os.path.join(self.temp_dir.name, 'test.epub')
        with open(self.attachment_file, 'w') as f:
            f.write("Test content")
            
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def test_load_config(self):
        """Test loading email configuration"""
        sender = EmailSender(self.config_path)
        self.assertEqual(sender.config["smtp_server"], "smtp.example.com")
        self.assertEqual(sender.config["to_email"], "recipient@example.com")
        
    @patch('src.email_sender.smtplib.SMTP')
    def test_send_email(self, mock_smtp):
        """Test sending email with mocked SMTP"""
        # Configure the mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        # Run the test
        sender = EmailSender(self.config_path)
        result = sender.send_email(self.attachment_file)
        
        # Verify the results
        self.assertTrue(result)
        mock_smtp_instance.login.assert_called_once_with(
            self.sample_config["username"], 
            self.sample_config["password"]
        )
        mock_smtp_instance.sendmail.assert_called_once()
        
    def test_dry_run_mode(self):
        """Test dry run mode doesn't actually send email"""
        sender = EmailSender(self.config_path, dry_run=True)
        result = sender.send_email(self.attachment_file)
        
        # In dry run mode, it should return True without error, but not send anything
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
