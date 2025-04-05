"""
Utility functions for the blog newsletter project.
"""

import os
import logging
import sys
from datetime import datetime
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored output
colorama.init()

def setup_directories():
    """
    Create the necessary directories if they don't exist.
    """
    # List of directories to create
    directories = [
        'data',
        'data/archive',
        'data/diffs',
        'output',
        'output/newsletters'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"{Fore.GREEN}Created directory: {directory}{Style.RESET_ALL}")

def setup_logging(log_level=logging.INFO):
    """
    Set up logging configuration.
    
    Args:
        log_level: The logging level to use.
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set up logging
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = f"logs/newsletter_{current_time}.log"
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Log the start of the session
    logging.info(f"Logging initialized. Log file: {log_file}")

def clean_html(html_content):
    """
    Clean HTML content by removing unnecessary elements.
    
    Args:
        html_content (str): HTML content to clean.
        
    Returns:
        str: Cleaned HTML content.
    """
    from bs4 import BeautifulSoup
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style elements
    for element in soup(['script', 'style', 'iframe', 'noscript']):
        element.decompose()
    
    # Remove comments
    comments = soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--'))
    for comment in comments:
        comment.extract()
    
    # Remove attributes that change frequently
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            # Keep href, src, and essential attributes, remove others
            if attr not in ['href', 'src', 'alt', 'title']:
                del tag[attr]
    
    # Return the cleaned HTML
    return str(soup)

def format_file_size(size_in_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_in_bytes (int): File size in bytes.
        
    Returns:
        str: Formatted file size.
    """
    # Convert bytes to KB, MB, etc.
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_in_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"

def get_domain_from_url(url):
    """
    Extract the domain from a URL.
    
    Args:
        url (str): URL to extract domain from.
        
    Returns:
        str: Domain name.
    """
    from urllib.parse import urlparse
    import re
    
    # Parse the URL
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Remove www. prefix if present
    domain = re.sub(r'^www\.', '', domain)
    
    return domain

def sanitize_filename(filename):
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename (str): String to sanitize.
        
    Returns:
        str: Sanitized filename.
    """
    import re
    
    # Replace invalid characters with underscore
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
    
    # Ensure filename is not too long
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized

def is_valid_url(url):
    """
    Check if a URL is valid.
    
    Args:
        url (str): URL to check.
        
    Returns:
        bool: True if URL is valid, False otherwise.
    """
    import validators
    
    return validators.url(url)
