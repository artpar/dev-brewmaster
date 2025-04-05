"""
Blog scraping functionality.
This module handles fetching blog content and saving it for later comparison.
"""

import os
import re
import time
import random
import logging
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
import validators

class BlogScraper:
    """Class for scraping blog content."""

    def __init__(self, user_agent=None, timeout=30, retry_attempts=3):
        """Initialize the scraper with configurable parameters."""
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.session = self._create_session()
        
    def _create_session(self):
        """Create and configure a requests session."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        return session
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def scrape(self, url):
        """
        Scrape the content from the given URL.
        
        Args:
            url (str): The URL to scrape.
            
        Returns:
            str: The HTML content of the page.
            
        Raises:
            ValueError: If the URL is invalid.
            requests.RequestException: If there's an error fetching the URL.
        """
        # Validate URL
        if not validators.url(url):
            raise ValueError(f"Invalid URL: {url}")
        
        logging.info(f"Fetching {url}")
        
        # Add a small random delay to avoid aggressive scraping
        time.sleep(random.uniform(1, 3))
        
        # Fetch the content
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        
        # Get the HTML content
        html_content = response.text
        
        # Parse with BeautifulSoup to clean and normalize
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove scripts, styles, and comments
        for element in soup(['script', 'style']):
            element.decompose()
        
        # Extract comment nodes (BeautifulSoup doesn't have a direct method)
        comments = soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--'))
        for comment in comments:
            comment.extract()
        
        # Return the cleaned HTML
        return str(soup)
    
    def get_domain(self, url):
        """Extract the domain from a URL for file organization."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        # Remove www. prefix if present
        domain = re.sub(r'^www\.', '', domain)
        return domain
    
    def save_content(self, url, content, date_str):
        """
        Save the scraped content to a file.
        
        Args:
            url (str): The URL that was scraped.
            content (str): The HTML content to save.
            date_str (str): Date string for the filename (YYYY-MM-DD).
        """
        domain = self.get_domain(url)
        
        # Create directory if it doesn't exist
        directory = f"data/archive/{domain}"
        os.makedirs(directory, exist_ok=True)
        
        # Save the content
        file_path = f"{directory}/{date_str}.html"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logging.info(f"Saved content to {file_path}")
        
    def get_previous_content(self, url):
        """
        Get the most recent previously scraped content for the URL.
        
        Args:
            url (str): The URL to find previous content for.
            
        Returns:
            tuple: (content, date) or (None, None) if no previous content exists.
        """
        domain = self.get_domain(url)
        directory = f"data/archive/{domain}"
        
        if not os.path.exists(directory):
            return None, None
        
        # Get all HTML files in the directory
        files = [f for f in os.listdir(directory) if f.endswith('.html')]
        
        if not files:
            return None, None
        
        # Sort files by date (the filename is YYYY-MM-DD.html)
        files.sort(reverse=True)
        
        # Skip the most recent file (it's likely the one we just saved)
        if len(files) > 1:
            previous_file = files[1]
        else:
            previous_file = files[0]
        
        # Load the content
        file_path = f"{directory}/{previous_file}"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Return the content and the date (without .html extension)
        date = previous_file.replace('.html', '')
        return content, date
