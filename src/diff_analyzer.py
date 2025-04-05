"""
Diff generation and analysis module.
This module handles comparing current and previous versions of a blog
to identify new content and extract relevant information.
"""

import os
import json
import logging
from datetime import datetime
import difflib
from bs4 import BeautifulSoup
import re

from scraper import BlogScraper

class DiffAnalyzer:
    """Class for analyzing differences between blog versions."""
    
    def __init__(self):
        """Initialize the diff analyzer."""
        self.scraper = BlogScraper()
    
    def generate_diff(self, url, current_date_str):
        """
        Generate a diff between the current and previous versions of a blog.
        
        Args:
            url (str): The URL of the blog.
            current_date_str (str): Current date string (YYYY-MM-DD).
            
        Returns:
            dict: Diff result containing changes and metadata.
        """
        domain = self.scraper.get_domain(url)
        
        # Get the current content
        current_file_path = f"data/archive/{domain}/{current_date_str}.html"
        if not os.path.exists(current_file_path):
            logging.error(f"Current content file not found: {current_file_path}")
            return None
        
        with open(current_file_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # Get the previous content
        previous_content, previous_date = self.scraper.get_previous_content(url)
        
        # If there's no previous content, consider everything as new
        if previous_content is None:
            logging.info(f"No previous content found for {url}, treating everything as new")
            
            # Extract articles from current content
            articles = self._extract_articles(current_content)
            
            diff_result = {
                'url': url,
                'domain': domain,
                'current_date': current_date_str,
                'previous_date': None,
                'has_changes': len(articles) > 0,
                'new_articles': articles,
                'changed_articles': [],
                'removed_articles': []
            }
        else:
            # Generate diff
            diff_result = self._compare_versions(
                previous_content, 
                current_content, 
                url, 
                domain, 
                previous_date, 
                current_date_str
            )
        
        # Save diff result
        self._save_diff_result(diff_result, domain, current_date_str)
        
        return diff_result
    
    def _compare_versions(self, previous_content, current_content, url, domain, previous_date, current_date_str):
        """
        Compare two versions of a blog to identify changes.
        
        Args:
            previous_content (str): HTML content of the previous version.
            current_content (str): HTML content of the current version.
            url (str): The URL of the blog.
            domain (str): The domain of the blog.
            previous_date (str): Date string of the previous version.
            current_date_str (str): Date string of the current version.
            
        Returns:
            dict: Diff result containing changes and metadata.
        """
        # Parse the HTML content
        prev_soup = BeautifulSoup(previous_content, 'lxml')
        curr_soup = BeautifulSoup(current_content, 'lxml')
        
        # Extract articles from both versions
        prev_articles = self._extract_articles(previous_content)
        curr_articles = self._extract_articles(current_content)
        
        # Map articles by title/URL for comparison
        prev_map = {art.get('url', art.get('title', '')): art for art in prev_articles}
        curr_map = {art.get('url', art.get('title', '')): art for art in curr_articles}
        
        # Identify new, changed, and removed articles
        new_articles = []
        changed_articles = []
        removed_articles = []
        
        # Find new and changed articles
        for key, curr_art in curr_map.items():
            if key not in prev_map:
                new_articles.append(curr_art)
            elif curr_art.get('content') != prev_map[key].get('content'):
                # Create a diff object
                diff_obj = {
                    'title': curr_art.get('title'),
                    'url': curr_art.get('url'),
                    'previous_content': prev_map[key].get('content'),
                    'current_content': curr_art.get('content')
                }
                changed_articles.append(diff_obj)
        
        # Find removed articles
        for key, prev_art in prev_map.items():
            if key not in curr_map:
                removed_articles.append(prev_art)
        
        # Create the diff result
        diff_result = {
            'url': url,
            'domain': domain,
            'current_date': current_date_str,
            'previous_date': previous_date,
            'has_changes': len(new_articles) > 0 or len(changed_articles) > 0 or len(removed_articles) > 0,
            'new_articles': new_articles,
            'changed_articles': changed_articles,
            'removed_articles': removed_articles
        }
        
        return diff_result
    
    def _extract_articles(self, html_content):
        """
        Extract articles from HTML content.
        
        Args:
            html_content (str): HTML content to extract articles from.
            
        Returns:
            list: List of article objects with title, URL, date, and content.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        articles = []
        
        # Different sites have different structures, so we'll try multiple selectors
        # Common article selectors
        article_selectors = [
            'article', '.post', '.entry', '.blog-post', '.blog-entry',
            '[class*="article"]', '[class*="post"]', '[class*="entry"]',
            '.card', '.item', '.news-item'
        ]
        
        # Try each selector
        for selector in article_selectors:
            article_elements = soup.select(selector)
            if article_elements:
                # Process found articles
                for element in article_elements:
                    article = self._extract_article_data(element)
                    if article and article.get('title'):  # Ensure we have at least a title
                        articles.append(article)
                
                # If we found articles, break the loop
                if articles:
                    break
        
        # If we couldn't find articles with selectors, try heuristic approach
        if not articles:
            # Look for heading elements followed by paragraphs
            headings = soup.find_all(['h1', 'h2', 'h3'])
            for heading in headings:
                # Check if this heading might be an article title
                if self._is_likely_article_title(heading):
                    article = self._extract_article_from_heading(heading)
                    if article and article.get('title'):
                        articles.append(article)
        
        return articles
    
    def _extract_article_data(self, element):
        """
        Extract article data from an HTML element.
        
        Args:
            element (BeautifulSoup.element): HTML element representing an article.
            
        Returns:
            dict: Article data including title, URL, date, and content.
        """
        article = {}
        
        # Extract title
        title_elem = element.select_one('h1, h2, h3, h4, .title, .entry-title')
        if title_elem:
            article['title'] = title_elem.get_text().strip()
            
            # Check for a link in the title
            link = title_elem.find('a')
            if link and link.has_attr('href'):
                article['url'] = link['href']
        
        # If no title found, try to find a link with some text
        if 'title' not in article:
            link = element.find('a', string=True)
            if link:
                article['title'] = link.get_text().strip()
                if link.has_attr('href'):
                    article['url'] = link['href']
        
        # Extract date
        date_elem = element.select_one('.date, .time, .entry-date, .published, time, [datetime]')
        if date_elem:
            if date_elem.has_attr('datetime'):
                article['date'] = date_elem['datetime']
            else:
                article['date'] = date_elem.get_text().strip()
        
        # Extract content
        content_elem = element.select_one('.content, .entry-content, .description, .summary, p')
        if content_elem:
            article['content'] = content_elem.get_text().strip()
        elif element.find('p'):
            # Get all paragraphs
            paragraphs = [p.get_text().strip() for p in element.find_all('p')]
            article['content'] = '\n'.join(paragraphs)
        
        # If we have a title but no content, get first paragraph after title
        if 'title' in article and 'content' not in article:
            title_elem = element.select_one('h1, h2, h3, h4, .title, .entry-title')
            if title_elem:
                next_p = title_elem.find_next('p')
                if next_p:
                    article['content'] = next_p.get_text().strip()
        
        return article
    
    def _is_likely_article_title(self, heading):
        """
        Check if a heading is likely to be an article title.
        
        Args:
            heading (BeautifulSoup.element): Heading element to check.
            
        Returns:
            bool: True if the heading is likely an article title.
        """
        # Check if it has reasonable length (not too short or too long)
        text = heading.get_text().strip()
        if len(text) < 10 or len(text) > 200:
            return False
        
        # Check if it has a link
        if heading.find('a'):
            return True
        
        # Check if it's followed by paragraphs
        next_p = heading.find_next('p')
        if next_p:
            return True
        
        return False
    
    def _extract_article_from_heading(self, heading):
        """
        Extract article data starting from a heading element.
        
        Args:
            heading (BeautifulSoup.element): Heading element to start from.
            
        Returns:
            dict: Article data including title, URL, date, and content.
        """
        article = {}
        
        # Extract title
        article['title'] = heading.get_text().strip()
        
        # Check for a link in the title
        link = heading.find('a')
        if link and link.has_attr('href'):
            article['url'] = link['href']
        
        # Look for date elements near the heading
        date_elem = heading.find_next(['time', '.date', '.published'])
        if date_elem:
            if date_elem.has_attr('datetime'):
                article['date'] = date_elem['datetime']
            else:
                article['date'] = date_elem.get_text().strip()
        
        # Extract content from paragraphs that follow
        paragraphs = []
        next_elem = heading.next_sibling
        while next_elem:
            if next_elem.name == 'p':
                paragraphs.append(next_elem.get_text().strip())
            # Stop if we hit another heading
            elif next_elem.name in ['h1', 'h2', 'h3', 'h4']:
                break
            next_elem = next_elem.next_sibling
        
        if paragraphs:
            article['content'] = '\n'.join(paragraphs)
        
        return article
    
    def _save_diff_result(self, diff_result, domain, date_str):
        """
        Save the diff result to a file.
        
        Args:
            diff_result (dict): The diff result to save.
            domain (str): Domain of the blog.
            date_str (str): Date string for the filename.
        """
        # Create directory if it doesn't exist
        directory = f"data/diffs/{domain}"
        os.makedirs(directory, exist_ok=True)
        
        # Save the diff result
        file_path = f"{directory}/{date_str}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(diff_result, f, indent=2)
        
        logging.info(f"Saved diff result to {file_path}")
