import os
import logging
import subprocess
import json
import tempfile
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EbookGenerator:
    def __init__(self):
        # Check if calibre command-line tools are installed
        self._verify_calibre_installed()
        
    def _verify_calibre_installed(self):
        """Verify that Calibre's command-line tools are installed."""
        try:
            subprocess.run(['ebook-convert', '--version'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          check=True)
            logger.info("Calibre command-line tools are installed")
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("Calibre command-line tools are not installed or not in PATH")
            raise RuntimeError("Calibre command-line tools are required but not found")
    
    def create_recipe_file(self, feeds_data: Dict[str, Any], output_dir: str) -> str:
        """
        Create a Calibre recipe file from the feeds data.
        Returns the path to the created recipe file.
        """
        recipe_path = os.path.join(output_dir, "daynews_recipe.recipe")
        
        recipe_content = f"""
#!/usr/bin/env python
# vim:fileencoding=utf-8

from calibre.web.feeds.recipes import BasicNewsRecipe

class DayNewsRecipe(BasicNewsRecipe):
    title = '{feeds_data["title"]}'
    oldest_article = 1
    max_articles_per_feed = 25
    auto_cleanup = True
    
    feeds = [
"""
        
        for feed in feeds_data['feeds']:
            recipe_content += f"        ('{feed['title']}', '{feed['url']}'),\n"
        
        recipe_content += "    ]"
        
        with open(recipe_path, 'w') as f:
            f.write(recipe_content)
            
        logger.info(f"Created recipe file at {recipe_path}")
        return recipe_path
        
    def generate_ebook(self, recipe_path: str, output_path: str) -> str:
        """
        Generate an EPUB file from a Calibre recipe.
        Returns the path to the generated EPUB file.
        """
        try:
            logger.info(f"Generating ebook using recipe {recipe_path}")
            
            # Run ebook-convert to generate the EPUB file
            result = subprocess.run(
                [
                    'ebook-convert', 
                    recipe_path, 
                    output_path,
                    '--output-profile=tablet',
                    '--prefer-metadata-cover'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            logger.info(f"Successfully generated ebook at {output_path}")
            logger.debug(f"ebook-convert output: {result.stdout}")
            
            return output_path
            
        except subprocess.SubprocessError as e:
            logger.error(f"Error generating ebook: {str(e)}")
            logger.error(f"Process output: {e.stdout}")
            logger.error(f"Process error: {e.stderr}")
            raise RuntimeError(f"Failed to generate ebook: {str(e)}")
