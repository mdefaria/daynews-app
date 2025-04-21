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
        """
        try:
            logger.info(f"Generating ebook using recipe {recipe_path}")
            
            # Verify recipe file exists
            if not os.path.isfile(recipe_path):
                error_msg = f"Recipe file not found: {recipe_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
                
            # Check if output directory exists, create if needed
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"Created output directory: {output_dir}")
                
            # Use simpler, more reliable command options
            # Avoid options that might not be supported in older Calibre versions
            cmd = [
                'ebook-convert', 
                recipe_path, 
                output_path,
                '--verbose'  # Keep this for debugging
            ]
            
            # Add minimal optimizations that are widely supported
            if low_memory:
                cmd.extend([
                    '--output-profile', 'mobile',
                    '--no-process-images'
                ])
                
            if show_progress:
                print("Starting ebook generation. This may take several minutes...")
                print("Running command:", " ".join(cmd))
                sys.stdout.flush()
                
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            # First, try running with --help to verify command works at all
            try:
                help_result = subprocess.run(
                    ['ebook-convert', '--help'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                if help_result.returncode != 0:
                    logger.warning(f"ebook-convert --help returned non-zero exit code: {help_result.returncode}")
                    logger.warning(f"stderr: {help_result.stderr}")
                else:
                    logger.debug("ebook-convert --help ran successfully")
            except Exception as e:
                logger.warning(f"Error when testing ebook-convert: {str(e)}")
                
            # Run process with real-time output monitoring
            start_time = time.time()
            
            # Enhanced process handling
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Variables to track progress
            feeds_processed = 0
            last_update = time.time()
            stdout_data = []
            stderr_data = []
            
            # Process output in real-time
            while process.poll() is None:  # While process is still running
                # Check if we've exceeded timeout
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    process.terminate()
                    msg = f"Process timed out after {timeout} seconds"
                    logger.error(msg)
                    if show_progress:
                        print(f"\n{msg}")
                    raise subprocess.TimeoutExpired(cmd, timeout)
                    
                # Capture stdout
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        stdout_data.append(line.strip())
                        logger.debug(f"STDOUT: {line.strip()}")
                        
                        # Progress indicators
                        if "Processing feed" in line:
                            feeds_processed += 1
                            if show_progress:
                                print(f"\nProcessing feed #{feeds_processed}...")
                                sys.stdout.flush()
                        elif show_progress:
                            if any(x in line.lower() for x in ["downloading", "fetching"]):
                                print(".", end="", flush=True)
                            elif "parsing" in line.lower():
                                print("P", end="", flush=True)
                            elif "converting" in line.lower():
                                print("C", end="", flush=True)
                
                # Capture stderr
                if process.stderr:
                    err_line = process.stderr.readline()
                    if err_line:
                        stderr_data.append(err_line.strip())
                        logger.debug(f"STDERR: {err_line.strip()}")
                        if show_progress and ("error" in err_line.lower() or "warning" in err_line.lower()):
                            print(f"\n{err_line.strip()}", file=sys.stderr, flush=True)
                
                # Show heartbeat
                if show_progress and time.time() - last_update > 10:
                    minutes, seconds = divmod(int(elapsed_time), 60)
                    print(f"\nStill working... Time elapsed: {minutes}m {seconds}s")
                    sys.stdout.flush()
                    last_update = time.time()
                    
                time.sleep(0.1)
            
            # Process has finished, get return code
            return_code = process.poll()
            
            # Get any remaining output
            remaining_stdout, remaining_stderr = process.communicate()
            if remaining_stdout:
                stdout_data.extend(remaining_stdout.splitlines())
            if remaining_stderr:
                stderr_data.extend(remaining_stderr.splitlines())
                
            if return_code != 0:
                # Enhanced error reporting
                error_msg = f"ebook-convert failed with exit code {return_code}"
                logger.error(error_msg)
                
                # Show detailed error information
                if stderr_data:
                    logger.error("Error output:")
                    for line in stderr_data:
                        logger.error(f"  {line}")
                        
                if show_progress:
                    print(f"\nError: {error_msg}")
                    print("Error details:")
                    for line in stderr_data[-10:]:  # Show last 10 error lines
                        print(f"  {line}")
                        
                # Troubleshooting suggestions
                print("\nTroubleshooting suggestions:")
                print("1. Check if the recipe file is correctly formatted")
                print("2. Verify that all URLs in the feeds are accessible")
                print("3. Try running with fewer feeds")
                print("4. Check if Calibre is correctly installed")
                print("5. Try running the command manually:")
                print(f"   {' '.join(cmd)}")
                
                raise subprocess.CalledProcessError(return_code, cmd)
            
            # Show final time
            total_time = time.time() - start_time
            minutes, seconds = divmod(int(total_time), 60)
            
            logger.info(f"Successfully generated ebook at {output_path}")
            if show_progress:
                print(f"\nEbook generation completed in {minutes}m {seconds}s")
                print(f"Ebook saved to: {output_path}")
            
            return output_path
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            raise RuntimeError(f"Failed to generate ebook: {str(e)}")
        except subprocess.TimeoutExpired:
            logger.error(f"Ebook generation timed out after {timeout} seconds")
            raise RuntimeError("Ebook generation timed out")
        except subprocess.SubprocessError as e:
            logger.error(f"Error generating ebook: {str(e)}")
            raise RuntimeError(f"Failed to generate ebook: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise RuntimeError(f"Failed to generate ebook: {str(e)}")
