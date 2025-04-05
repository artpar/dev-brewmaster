"""
Newsletter generation module.
This module uses an LLM to generate a newsletter based on the diffs.
"""

import os
import json
import logging
from datetime import datetime
import openai
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class NewsletterGenerator:
    """Class for generating newsletters using an LLM."""
    
    def __init__(self, model="gpt-4-turbo"):
        """
        Initialize the newsletter generator.
        
        Args:
            model (str): The OpenAI model to use.
        """
        self.model = model
        # Get API key from environment variable
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logging.warning("OPENAI_API_KEY environment variable not set")
    
    def generate(self, diff_results, date_str):
        """
        Generate a newsletter based on the diff results.
        
        Args:
            diff_results (list): List of diff results from multiple blogs.
            date_str (str): Date string for the newsletter.
            
        Returns:
            str: Generated newsletter markdown.
        """
        if not self.api_key:
            logging.error("Cannot generate newsletter: OPENAI_API_KEY not set")
            return self._generate_fallback_newsletter(diff_results, date_str)
        
        # Group diff results by category
        categorized_diffs = self._categorize_diffs(diff_results)
        
        # Generate newsletter sections for each category
        sections = []
        for category, diffs in categorized_diffs.items():
            section = self._generate_category_section(category, diffs)
            sections.append(section)
        
        # Combine sections into a complete newsletter
        newsletter = self._compile_newsletter(sections, date_str)
        
        return newsletter
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.APITimeoutError, openai.APIConnectionError))
    )
    def _generate_category_section(self, category, diffs):
        """
        Generate a newsletter section for a category using the LLM.
        
        Args:
            category (str): The category name.
            diffs (list): List of diff results for this category.
            
        Returns:
            dict: Generated section with title and content.
        """
        # Prepare the data for the LLM
        prompt_data = self._prepare_prompt_data(category, diffs)
        
        # Call the OpenAI API
        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": self._get_user_prompt(prompt_data)}
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Extract the generated content
            content = response.choices[0].message.content.strip()
            
            # Return the section
            return {
                "category": category,
                "title": category.capitalize(),
                "content": content
            }
            
        except Exception as e:
            logging.error(f"Error generating newsletter section for {category}: {e}")
            # Fallback: generate a simple section
            return self._generate_fallback_section(category, diffs)
    
    def _get_system_prompt(self):
        """Get the system prompt for the LLM."""
        return """
        You are a newsletter writer for a tech blog aggregator. Your task is to write a section of the newsletter
        summarizing new and changed articles from various blogs. The summary should be informative and concise.
        
        Follow these guidelines:
        - Use a engaging but professional writing style
        - Include key information about the articles
        - Group related articles together
        - Highlight the most important or interesting updates
        - Format your response in Markdown
        - Provide proper links to the articles
        """
    
    def _get_user_prompt(self, prompt_data):
        """
        Generate the user prompt based on the data.
        
        Args:
            prompt_data (dict): Data prepared for the prompt.
            
        Returns:
            str: The user prompt.
        """
        prompt = f"Write a newsletter section for the category: {prompt_data['category']}\n\n"
        
        # Add blogs info
        prompt += "Blogs with updates:\n"
        for blog in prompt_data['blogs']:
            prompt += f"- {blog['name']} ({blog['url']})\n"
        
        # Add new articles
        if prompt_data['new_articles']:
            prompt += "\nNew Articles:\n"
            for article in prompt_data['new_articles']:
                prompt += f"- '{article['title']}'"
                if 'url' in article:
                    prompt += f" (URL: {article['url']})"
                if 'content' in article:
                    # Truncate content to a reasonable length
                    content = article['content'][:300] + "..." if len(article['content']) > 300 else article['content']
                    prompt += f"\n  Summary: {content}\n"
                prompt += "\n"
        
        # Add changed articles
        if prompt_data['changed_articles']:
            prompt += "\nChanged Articles:\n"
            for article in prompt_data['changed_articles']:
                prompt += f"- '{article['title']}'"
                if 'url' in article:
                    prompt += f" (URL: {article['url']})"
                prompt += "\n"
        
        # Add instructions
        prompt += """
        Generate a newsletter section summarizing these updates. The section should:
        1. Have a catchy subtitle related to the category
        2. Summarize the most important updates
        3. Be written in Markdown format
        4. Include proper links to articles
        5. Be between 200-300 words
        """
        
        return prompt
    
    def _prepare_prompt_data(self, category, diffs):
        """
        Prepare the data for the LLM prompt.
        
        Args:
            category (str): The category name.
            diffs (list): List of diff results for this category.
            
        Returns:
            dict: Data prepared for the prompt.
        """
        blogs = []
        new_articles = []
        changed_articles = []
        
        for diff in diffs:
            # Add blog info
            blogs.append({
                "name": diff.get('blog_name', diff.get('domain', 'Unknown')),
                "url": diff.get('blog_url', diff.get('url', ''))
            })
            
            # Add new articles
            for article in diff.get('new_articles', []):
                new_articles.append({
                    "title": article.get('title', 'Untitled'),
                    "url": article.get('url', ''),
                    "content": article.get('content', ''),
                    "date": article.get('date', ''),
                    "blog": diff.get('blog_name', diff.get('domain', 'Unknown'))
                })
            
            # Add changed articles
            for article in diff.get('changed_articles', []):
                changed_articles.append({
                    "title": article.get('title', 'Untitled'),
                    "url": article.get('url', ''),
                    "blog": diff.get('blog_name', diff.get('domain', 'Unknown'))
                })
        
        return {
            "category": category,
            "blogs": blogs,
            "new_articles": new_articles,
            "changed_articles": changed_articles
        }
    
    def _categorize_diffs(self, diff_results):
        """
        Group diff results by category.
        
        Args:
            diff_results (list): List of diff results from multiple blogs.
            
        Returns:
            dict: Diff results grouped by category.
        """
        categorized = {}
        
        for diff in diff_results:
            category = diff.get('category', 'general')
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(diff)
        
        return categorized
    
    def _compile_newsletter(self, sections, date_str):
        """
        Compile sections into a complete newsletter.
        
        Args:
            sections (list): List of generated sections.
            date_str (str): Date string for the newsletter.
            
        Returns:
            str: Complete newsletter in markdown format.
        """
        # Format date for display (e.g., "April 5, 2025")
        display_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
        
        # Create newsletter header
        header = f"""# Tech Blog Newsletter
## Issue: {display_date}

Welcome to this week's tech blog update! Here's what's new and noteworthy from the tech blogosphere.

"""
        
        # Add sections
        content = header
        for section in sections:
            content += f"## {section['title']}\n\n"
            content += section['content']
            content += "\n\n---\n\n"
        
        # Add footer
        footer = """
*This newsletter is auto-generated based on updates from tech blogs across the web.*

*To unsubscribe or provide feedback, please reply to this email.*
"""
        
        content += footer
        
        return content
    
    def _generate_fallback_newsletter(self, diff_results, date_str):
        """
        Generate a simple newsletter without using the LLM.
        
        Args:
            diff_results (list): List of diff results from multiple blogs.
            date_str (str): Date string for the newsletter.
            
        Returns:
            str: Generated newsletter markdown.
        """
        # Format date for display
        display_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')
        
        # Create newsletter header
        content = f"""# Tech Blog Newsletter
## Issue: {display_date}

Welcome to this week's tech blog update! Here's what's new from the tech blogosphere.

"""
        
        # Group by blog
        for diff in diff_results:
            blog_name = diff.get('blog_name', diff.get('domain', 'Unknown'))
            blog_url = diff.get('blog_url', diff.get('url', ''))
            
            content += f"## Updates from [{blog_name}]({blog_url})\n\n"
            
            # New articles
            if diff.get('new_articles'):
                content += "### New Articles\n\n"
                for article in diff['new_articles']:
                    title = article.get('title', 'Untitled')
                    url = article.get('url', '')
                    
                    if url:
                        content += f"- [{title}]({url})\n"
                    else:
                        content += f"- {title}\n"
                
                content += "\n"
            
            # Changed articles
            if diff.get('changed_articles'):
                content += "### Updated Articles\n\n"
                for article in diff['changed_articles']:
                    title = article.get('title', 'Untitled')
                    url = article.get('url', '')
                    
                    if url:
                        content += f"- [{title}]({url})\n"
                    else:
                        content += f"- {title}\n"
                
                content += "\n"
            
            content += "---\n\n"
        
        # Add footer
        footer = """
*This newsletter is auto-generated based on updates from tech blogs across the web.*

*To unsubscribe or provide feedback, please reply to this email.*
"""
        
        content += footer
        
        return content
        
    def _generate_fallback_section(self, category, diffs):
        """
        Generate a simple section without using the LLM.
        
        Args:
            category (str): The category name.
            diffs (list): List of diff results for this category.
            
        Returns:
            dict: Generated section with title and content.
        """
        content = f"### Updates in {category.capitalize()}\n\n"
        
        for diff in diffs:
            blog_name = diff.get('blog_name', diff.get('domain', 'Unknown'))
            blog_url = diff.get('blog_url', diff.get('url', ''))
            
            content += f"#### [{blog_name}]({blog_url})\n\n"
            
            # New articles
            if diff.get('new_articles'):
                for article in diff['new_articles']:
                    title = article.get('title', 'Untitled')
                    url = article.get('url', '')
                    
                    if url:
                        content += f"- [{title}]({url})\n"
                    else:
                        content += f"- {title}\n"
            
            content += "\n"
        
        return {
            "category": category,
            "title": category.capitalize(),
            "content": content
        }
