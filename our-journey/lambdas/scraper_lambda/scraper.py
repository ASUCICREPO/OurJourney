import logging
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from constants import (
    SCRAPER_URLS, PDF_SOURCE_URL,
    HTTP_HEADERS, HTTP_TIMEOUT, PDF_TIMEOUT,
    PAGE_SCRAPE_DELAY, PDF_DOWNLOAD_DELAY
)
from s3_utils import upload_text_to_s3, upload_pdf_to_s3
from dynamo_utils import upsert_county_pdf

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# WEB SCRAPING FUNCTIONS
# ============================================================================

def scrape_html_pages():
    """
    Scrape all HTML pages from SCRAPER_URLS and upload to S3.
    
    Returns:
        int: Number of successfully scraped pages
    """
    logger.info(f"Scraping {len(SCRAPER_URLS)} HTML pages")
    success_count = 0
    
    for filename, url in SCRAPER_URLS.items():
        try:
            logger.info(f"Scraping: {url}")
            
            # Fetch HTML
            response = requests.get(url, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            # Extract content
            text_content = extract_main_content(response.content, url, filename)
            
            # Upload to S3
            upload_text_to_s3(filename, text_content)
            
            success_count += 1
            logger.info(f"✓ Successfully scraped and uploaded: {filename}")
            
            # Be polite - wait between requests
            time.sleep(PAGE_SCRAPE_DELAY)
            
        except Exception as e:
            logger.error(f"✗ Failed to scrape {url}: {str(e)}")
            # Continue with other pages
    
    return success_count


def extract_main_content(html_content, url, page_name):
    """
    Extract main content from HTML page.
    
    Args:
        html_content: Raw HTML bytes
        url: Source URL
        page_name: Name for the page
        
    Returns:
        str: Formatted text content with metadata header
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()
    
    # Extract page title
    title = soup.find('title')
    title_text = title.get_text(strip=True) if title else page_name.replace('-', ' ').title()
    
    # Find main content area
    main_content = soup.find('main') or soup.find('article') or soup.find('body')
    
    if not main_content:
        return ""
    
    # Extract text
    text = main_content.get_text(separator='\n', strip=True)
    
    # Clean up whitespace
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    content_text = '\n'.join(cleaned_lines)
    
    # Create output with metadata header
    output = f"""Source: {url}
Title: {title_text}
Scraped: {datetime.now().strftime('%Y-%m-%d')}

{content_text}"""
    
    return output


def discover_and_download_pdfs():
    """
    Discover PDF links from the reentry resource guides page and download them.
    Each PDF is associated with a county name extracted from the page's heading text.
    After a successful upload the county -> PDF mapping is written to DynamoDB.

    Returns:
        tuple: (pdfs_downloaded: int, county_mappings_saved: int)
    """
    logger.info(f"Discovering PDFs from: {PDF_SOURCE_URL}")

    try:
        # Fetch the page containing PDF links
        response = requests.get(PDF_SOURCE_URL, headers=HTTP_HEADERS, timeout=HTTP_TIMEOUT)
        response.raise_for_status()

        # Discover (county, url) pairs
        pdf_entries = discover_pdf_links(response.content, PDF_SOURCE_URL)
        logger.info(f"Found {len(pdf_entries)} PDF link(s)")

        if not pdf_entries:
            logger.warning("No PDF links found")
            return 0, 0

        pdfs_downloaded = 0
        county_mappings_saved = 0

        for i, (county_name, pdf_url) in enumerate(pdf_entries, 1):
            try:
                logger.info(f"[{i}/{len(pdf_entries)}] Downloading PDF for {county_name}: {pdf_url}")

                success, s3_key, content = download_pdf(pdf_url, county_name)

                if success:
                    upload_pdf_to_s3(s3_key, content)
                    pdfs_downloaded += 1
                    logger.info(f"✓ Downloaded and uploaded: {s3_key}")

                    saved = upsert_county_pdf(county_name, s3_key, pdf_url)
                    if saved:
                        county_mappings_saved += 1
                    else:
                        logger.warning(f"PDF uploaded but DynamoDB write failed for: {county_name}")

                # Be polite - wait between downloads
                time.sleep(PDF_DOWNLOAD_DELAY)

            except Exception as e:
                logger.error(f"✗ Failed to process PDF for {county_name} ({pdf_url}): {str(e)}")
                # Continue with other counties

        return pdfs_downloaded, county_mappings_saved

    except Exception as e:
        logger.error(f"Error in PDF discovery/download: {str(e)}")
        return 0, 0


def discover_pdf_links(html_content, base_url):
    """
    Discover all PDF links on the reentry resource guides page, pairing each
    with its county name from the heading text immediately following the link.

    The page structure for every county is:
        <a href="...county.pdf"><img alt="CountyName.png"></a>
        <h2><a href="...county.pdf">CountyName</a></h2>

    We use the <h2> anchor text as the authoritative county name because the
    PDF URLs are opaque Wix hashes that contain no county information.

    Args:
        html_content: Raw HTML bytes
        base_url: Base URL for resolving relative links

    Returns:
        list of (county_name: str, absolute_url: str) tuples, deduplicated
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    entries = []
    seen_urls = set()

    for heading in soup.find_all('h2'):
        link = heading.find('a', href=True)
        if not link:
            continue

        href = link['href']
        if not href.lower().endswith('.pdf'):
            continue

        county_name = link.get_text(strip=True)
        if not county_name:
            continue

        absolute_url = urljoin(base_url, href)

        # Deduplicate by URL (image link and heading link both point to same PDF)
        if absolute_url not in seen_urls:
            seen_urls.add(absolute_url)
            entries.append((county_name, absolute_url))
            logger.debug(f"Found PDF for county '{county_name}': {absolute_url}")

    return entries


def download_pdf(url, county_name):
    """
    Download a PDF file from a URL.

    Args:
        url: PDF URL to download
        county_name: County name used to generate a human-readable S3 key

    Returns:
        tuple: (success: bool, s3_key: str, content: bytes)
    """
    try:
        s3_key = county_name_to_s3_key(county_name)

        response = requests.get(url, headers=HTTP_HEADERS, timeout=PDF_TIMEOUT, stream=True)
        response.raise_for_status()

        content = response.content
        file_size_kb = len(content) / 1024
        logger.debug(f"Downloaded {s3_key} ({file_size_kb:.1f} KB)")

        return True, s3_key, content

    except Exception as e:
        logger.error(f"Error downloading PDF for '{county_name}': {str(e)}")
        return False, None, None


# ============================================================================
# UTILITY HELPERS
# ============================================================================

def county_name_to_s3_key(county_name):
    """
    Convert a county name to a clean, consistent S3 object key.
    e.g. "New Hanover" -> "new-hanover.pdf"
         "Wake"        -> "wake.pdf"

    Args:
        county_name: Human-readable county name from the page heading

    Returns:
        str: S3 object key with .pdf extension
    """
    slug = county_name.strip().lower().replace(' ', '-')
    return f"{slug}.pdf"