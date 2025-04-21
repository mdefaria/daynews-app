import os
import logging
import subprocess
import json
import tempfile
import time
import sys
from typing import Dict, Any, Optional, List, Tuple

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
        
        # Limit articles per feed for faster processing
        max_articles_per_feed = 10  # Reduced from 25
        
        recipe_content = f"""
#!/usr/bin/env python
# vim:fileencoding=utf-8

from calibre.web.feeds.recipes import BasicNewsRecipe

class DayNewsRecipe(BasicNewsRecipe):
    title = '{feeds_data["title"]}'
    oldest_article = 1
    max_articles_per_feed = {max_articles_per_feed}
    auto_cleanup = True
    
    # Optimization settings
    simultaneous_downloads = 2  # Reduce to prevent memory issues
    delay = 0.2  # Small delay between fetches to reduce load
    timefmt = ''  # Skip date formatting to save processing
    no_stylesheets = True  # Skip CSS processing
    remove_javascript = True  # Skip JS
    scale_news_images = (400, 400)  # Smaller images
    
    feeds = [
"""
        
        for feed in feeds_data['feeds']:
            recipe_content += f"        ('{feed['title']}', '{feed['url']}'),\n"
        
        recipe_content += "    ]"
        
        with open(recipe_path, 'w') as f:
            f.write(recipe_content)
            
        logger.info(f"Created recipe file at {recipe_path}")
        return recipe_path
        
    def generate_ebook(self, recipe_path: str, output_path: str, 
                       low_memory: bool = True, timeout: int = 300,
                       max_articles: int = 10, image_size: int = 400,
                       show_progress: bool = True) -> str:
        """
        Generate an EPUB file from a Calibre recipe.
        Returns the path to the generated EPUB file.
        
        Args:
            recipe_path: Path to the Calibre recipe file
            output_path: Path where the EPUB should be saved
            low_memory: Whether to use low memory optimizations
            timeout: Maximum time in seconds to allow for conversion
            max_articles: Maximum number of articles to process
            image_size: Maximum size for images in pixels
            show_progress: Whether to display a progress indicator
        """
        try:
            logger.info(f"Generating ebook using recipe {recipe_path}")
            
            # Base conversion command with corrected syntax
            cmd = [
                'ebook-convert', 
                recipe_path, 
                output_path,
                '--output-profile', 'mobile',  # Fixed format (separate arguments)
                '--max-toc-links', str(max_articles),
                '--verbose',
                '--rescale-images', str(image_size),  # Removed 'x' format
                '--linearize-tables',
                '--timeout', '10',
                # Removed --test flag (not valid for ebook-convert)
                '--base-font-size', '10'
            ]
            
            # Add low memory optimizations if requested
            if low_memory:
                cmd.extend([
                    '--no-process-images',
                    '--disable-font-rescaling',
                    '--dont-compress',
                    '--keep-ligatures'
                ])
            
            # Add progressive mode settings
            if show_progress:
                print("Starting ebook generation. This may take several minutes...")
                print("Progress indicators: '.' = downloading, 'P' = parsing, 'C' = converting")
                sys.stdout.flush()
            
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            # Run process with real-time output monitoring
            start_time = time.time()
            
            # Start process with pipe for stdout and stderr
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Variables to track progress
            elapsed_time = 0
            feeds_processed = 0
            last_update = time.time()
            
            # Process output in real-time
            while process.poll() is None:  # While process is still running
                # Check if we've exceeded timeout
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    process.terminate()
                    raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)
                
                # Check for stdout output
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        # Log significant events
                        if "Processing feed" in line:
                            feeds_processed += 1
                            if show_progress:
                                print(f"\nProcessing feed #{feeds_processed}...")
                                sys.stdout.flush()
                        if show_progress and any(x in line.lower() for x in ["downloading", "fetching", "getting"]):
                            print(".", end="", flush=True)
                        if show_progress and "parsing" in line.lower():
                            print("P", end="", flush=True)
                        if show_progress and "converting" in line.lower():
                            print("C", end="", flush=True)
                        
                        # Keep more detailed logs in debug
                        logger.debug(f"STDOUT: {line.strip()}")
                
                # Check for stderr output - important for error diagnosis
                if process.stderr:
                    err_line = process.stderr.readline()
                    if err_line:
                        logger.debug(f"STDERR: {err_line.strip()}")
                        # Print errors in real-time if showing progress
                        if show_progress and "error" in err_line.lower():
                            print(f"\nERROR: {err_line.strip()}", file=sys.stderr)
                
                # Show heartbeat every 10 seconds
                if show_progress and time.time() - last_update > 10:
                    minutes, seconds = divmod(int(elapsed_time), 60)
                    print(f"\nStill working... Time elapsed: {minutes}m {seconds}s")
                    sys.stdout.flush()
                    last_update = time.time()
                
                # Sleep briefly to avoid high CPU usage
                time.sleep(0.1)
            
            # Process has finished, get return code
            return_code = process.poll()
            
            # Get any remaining output
            stdout, stderr = process.communicate()
            
            if return_code != 0:
                logger.error(f"Process failed with code {return_code}")
                logger.error(f"Error output: {stderr}")
                if show_progress:
                    print(f"\nError: ebook-convert failed with code {return_code}")
                    print(f"Error details: {stderr}")
                raise subprocess.CalledProcessError(return_code, cmd, stdout, stderr)
            
            # Show final time
            total_time = time.time() - start_time
            minutes, seconds = divmod(int(total_time), 60)
            
            logger.info(f"Successfully generated ebook at {output_path}")
            if show_progress:
                print(f"\nEbook generation completed in {minutes}m {seconds}s")
                print(f"Ebook saved to: {output_path}")
            
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error(f"Ebook generation timed out after {timeout} seconds")
            raise RuntimeError("Ebook generation timed out")
        except subprocess.SubprocessError as e:
            logger.error(f"Error generating ebook: {str(e)}")
            if hasattr(e, 'stdout') and e.stdout:
                logger.error(f"Process output: {e.stdout}")
            if hasattr(e, 'stderr') and e.stderr:
                logger.error(f"Process error: {e.stderr}")
            raise RuntimeError(f"Failed to generate ebook: {str(e)}")
