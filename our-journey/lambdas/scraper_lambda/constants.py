import os
import logging

"""
Constants for OurJourney Scraper Lambda Function
This module contains configuration constants for web scraping and Knowledge Base synchronization
"""

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
# Logging configuration - change LOG_LEVEL to control all modules
LOG_LEVEL = logging.INFO  # or logging.DEBUG, logging.WARNING, etc.
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'

def setup_logging():
    """Configure logging for the entire application"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        force=True  # Override any existing configuration
    )

# Call setup when constants is imported
setup_logging()

# ============================================================================
# CLOUDFORMATION RESPONSE CONSTANTS
# ============================================================================
# CloudFormation custom resource response statuses
CFN_SUCCESS = "SUCCESS"
CFN_FAILED = "FAILED"

# Standard response messages
RESPONSE_MESSAGES = {
    "CREATE_SUCCESS": "Scrape and sync operation completed successfully",
    "UPDATE_SUCCESS": "Update operation completed successfully (no-op)", 
    "DELETE_SUCCESS": "Delete operation completed successfully (no-op)",
    "GENERIC_SUCCESS": "operation completed successfully",
    "ENV_VAR_MISSING": "Required environment variable is not set",
    "SCRAPE_SUCCESS": "Website scraping completed successfully",
    "SCRAPE_ERROR": "Error during website scraping",
    "PDF_DISCOVERY_SUCCESS": "PDF links discovered successfully",
    "PDF_DISCOVERY_ERROR": "Error discovering PDF links",
    "PDF_DOWNLOAD_SUCCESS": "PDF files downloaded successfully",
    "PDF_DOWNLOAD_ERROR": "Error downloading PDF files",
    "S3_CLEAR_SUCCESS": "S3 bucket cleared successfully",
    "S3_CLEAR_ERROR": "Error clearing S3 bucket",
    "S3_UPLOAD_SUCCESS": "Files uploaded to S3 successfully",
    "S3_UPLOAD_ERROR": "Error uploading files to S3",
    "INGESTION_STARTED": "Knowledge Base ingestion job started",
    "INGESTION_START_ERROR": "Error starting Knowledge Base ingestion job",
    "INGESTION_COMPLETE": "Knowledge Base ingestion completed successfully",
    "INGESTION_FAILED": "Knowledge Base ingestion failed",
    "INGESTION_TIMEOUT": "Ingestion job started but not waiting for completion due to timeout",
    "DATA_SOURCE_ERROR": "Error retrieving data source ID",
}

# ============================================================================
# ENVIRONMENT VARIABLE VALIDATION
# ============================================================================
# Required environment variables with validation
DOC_BUCKET_NAME = os.environ.get("DOC_BUCKET_NAME")
if not DOC_BUCKET_NAME:
    raise ValueError("DOC_BUCKET_NAME environment variable is required")

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")
if not KNOWLEDGE_BASE_ID:
    raise ValueError("KNOWLEDGE_BASE_ID environment variable is required")

AWS_REGION = os.environ.get("AWS_REGION")
if not AWS_REGION:
    raise ValueError("AWS_REGION environment variable is required")

COUNTY_RESOURCES_TABLE_NAME = os.environ.get("COUNTY_RESOURCES_TABLE")
if not COUNTY_RESOURCES_TABLE_NAME:
    raise ValueError("COUNTY_RESOURCES_TABLE environment variable is required")

# ============================================================================
# SCRAPER CONFIGURATION CONSTANTS
# ============================================================================
# URLs to scrape from OurJourney website
SCRAPER_URLS = {
    'home-plan-assistance': 'https://www.ourjourney2gether.com/home-plan-assistance',
    'find-a-job': 'https://www.ourjourney2gether.com/find-a-job',
    'essential-services': 'https://www.ourjourney2gether.com/essential-services',
    'mat-assistance': 'https://www.ourjourney2gether.com/mat-assistance',
    'reentry-resource-guides': 'https://www.ourjourney2gether.com/reentry-resource-guides'
}

# URL that contains PDF links to download
PDF_SOURCE_URL = 'https://www.ourjourney2gether.com/reentry-resource-guides'

# HTTP request configuration
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

HTTP_TIMEOUT = 30  # seconds for HTML requests
PDF_TIMEOUT = 60   # seconds for PDF downloads

# Polite scraping delays (seconds)
PAGE_SCRAPE_DELAY = 2  # Between HTML page scrapes
PDF_DOWNLOAD_DELAY = 1  # Between PDF downloads

# ============================================================================
# S3 CONFIGURATION CONSTANTS
# ============================================================================
# S3 batch delete limit (AWS maximum)
S3_DELETE_BATCH_SIZE = 1000

# File prefixes for organization
TEXT_FILE_SUFFIX = ".txt"
PDF_FILE_SUFFIX = ".pdf"

# ============================================================================
# BEDROCK KNOWLEDGE BASE CONFIGURATION
# ============================================================================
# Ingestion job polling configuration
INGESTION_POLL_INTERVAL = 10  # seconds between status checks
INGESTION_MAX_WAIT_TIME = 600  # 10 minutes max wait for ingestion (leave buffer for Lambda timeout)

# Ingestion job statuses
INGESTION_STATUS_STARTING = "STARTING"
INGESTION_STATUS_IN_PROGRESS = "IN_PROGRESS"
INGESTION_STATUS_COMPLETE = "COMPLETE"
INGESTION_STATUS_FAILED = "FAILED"

# ============================================================================
# LAMBDA TIMEOUT CONFIGURATION
# ============================================================================
# Time buffer to ensure Lambda can respond before timeout (seconds)
LAMBDA_TIMEOUT_BUFFER = 120  # 2 minutes buffer before 15-minute timeout