#!/usr/bin/env python3
"""
Main execution script for the blog newsletter generator.
This script orchestrates the entire process:
1. Loading blog URLs
2. Scraping the blogs
3. Generating diffs
4. Creating the newsletter
"""

import os
import json
import logging
from datetime import datetime
import traceback
from dotenv import load_dotenv
from tqdm import tqdm

from scraper import BlogScraper
from diff_analyzer import DiffAnalyzer
from newsletter_generator import NewsletterGenerator
from utils import setup_directories, setup_logging

# Load environment variables from .env file if present
load_dotenv()

def load_blog_urls(file_path="data/blogs.json"):
    """Load blog URLs from the JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data.get('blogs', [])
    except Exception as e:
        logging.error(f"Error loading blog URLs: {e}")
        return []

def main():
    """Main execution function."""
    # Get current date for filenames
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Setup directories and logging
    setup_directories()
    setup_logging()
    
    # Log start of process
    logging.info(f"Starting blog newsletter generation process on {current_date}")
    
    try:
        # Load blog URLs
        logging.info("Loading blog URLs...")
        blogs = load_blog_urls()
        logging.info(f"Loaded {len(blogs)} blog URLs")
        
        # Initialize components
        scraper = BlogScraper()
        diff_analyzer = DiffAnalyzer()
        newsletter_generator = NewsletterGenerator()
        
        # Process each blog
        logging.info("Processing blogs...")
        all_diffs = []
        
        for blog in tqdm(blogs, desc="Processing blogs"):
            try:
                # Extract domain for file organization
                url = blog['url']
                name = blog['name']
                category = blog.get('category', 'general')
                
                # Scrape blog
                logging.info(f"Scraping {name} ({url})...")
                html_content = scraper.scrape(url)
                
                # Save the content
                scraper.save_content(url, html_content, current_date)
                
                # Generate diff
                logging.info(f"Generating diff for {name}...")
                diff_result = diff_analyzer.generate_diff(url, current_date)
                
                if diff_result and diff_result.get('has_changes', False):
                    logging.info(f"Found changes in {name}")
                    # Add blog metadata to diff result
                    diff_result['blog_name'] = name
                    diff_result['blog_url'] = url
                    diff_result['category'] = category
                    all_diffs.append(diff_result)
                else:
                    logging.info(f"No changes found in {name}")
                    
            except Exception as e:
                logging.error(f"Error processing {blog.get('name', blog.get('url', 'unknown'))}: {e}")
                logging.debug(traceback.format_exc())
                continue
        
        # Generate newsletter if there are any diffs
        if all_diffs:
            logging.info(f"Generating newsletter with {len(all_diffs)} blog updates...")
            newsletter = newsletter_generator.generate(all_diffs, current_date)
            
            # Save newsletter
            newsletter_path = f"output/newsletters/{current_date}.md"
            with open(newsletter_path, 'w') as f:
                f.write(newsletter)
            logging.info(f"Newsletter saved to {newsletter_path}")
        else:
            logging.info("No blog updates found, skipping newsletter generation")
        
        logging.info("Blog newsletter generation process completed successfully")
        
    except Exception as e:
        logging.error(f"Error in main process: {e}")
        logging.debug(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
