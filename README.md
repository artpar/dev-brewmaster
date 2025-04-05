# Blog Newsletter Generator

An automated system that scrapes blogs, identifies new content, and generates weekly newsletters.

## Overview

This project creates an automated newsletter system that:

1. Scrapes a list of configured blog URLs weekly
2. Compares current content with previous versions to identify new and changed articles
3. Uses an LLM (OpenAI's GPT) to generate a newsletter summarizing the changes
4. Stores everything in the repository and runs automatically via GitHub Actions

## Project Structure

```
blog-newsletter/
├── .github/workflows/       # GitHub Actions workflow configuration
├── data/                    # Data storage
│   ├── blogs.json           # List of blog URLs to track
│   ├── archive/             # Archived versions of blogs
│   └── diffs/               # Diff results between versions
├── output/                  # Generated newsletters
├── src/                     # Source code
├── tests/                   # Tests
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Setup

### Prerequisites

- Python 3.10 or higher
- A GitHub account
- An OpenAI API key for newsletter generation

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-username/blog-newsletter.git
   cd blog-newsletter
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Create a `.env` file with your OpenAI API key:
     ```
     OPENAI_API_KEY=your_api_key_here
     ```
   - For GitHub Actions, add the API key as a repository secret named `OPENAI_API_KEY`

4. Configure your blog list:
   - Edit `data/blogs.json` to add or remove blogs you want to track
   - Each blog should have a URL, name, and category

### Running Locally

To run the newsletter generator manually:

```
python -m src/main
```

This will:
1. Scrape all blogs in `data/blogs.json`
2. Generate diffs by comparing with previous versions
3. Create a newsletter in `output/newsletters/`

## Automated Workflow

The GitHub Actions workflow is configured to run:
- Weekly (every Sunday at midnight)
- When changes are pushed to the main branch
- When the blog list is updated
- Manually via the "Run workflow" button in GitHub

## Components

- **scraper.py**: Handles fetching blog content and saving it
- **diff_analyzer.py**: Compares versions to identify new and changed content
- **newsletter_generator.py**: Uses OpenAI to generate the newsletter
- **main.py**: Orchestrates the entire process
- **utils.py**: Contains helper functions

## Newsletter Format

The generated newsletters are in Markdown format and include:
- A header with date and introduction
- Sections for each category of blogs
- Lists of new and updated articles with links
- A footer

## Customization

- **Blog List**: Edit `data/blogs.json` to manage which blogs to track
- **Newsletter Style**: Modify the prompts in `newsletter_generator.py`
- **Scheduling**: Change the cron schedule in `.github/workflows/scrape.yml`

## License

MIT License

## Contributions

Contributions are welcome! Please feel free to submit a Pull Request.
