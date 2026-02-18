import logging
import traceback
from constants import LAMBDA_TIMEOUT_BUFFER
from s3_utils import clear_s3_bucket
from scraper import scrape_html_pages, discover_and_download_pdfs
from kb_utils import start_kb_ingestion, wait_for_ingestion, get_remaining_time_seconds

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# MAIN ORCHESTRATION FUNCTION
# ============================================================================

def scrape_and_sync(event, context, is_custom_resource=False):
    """
    Main orchestration function for scraping and syncing Knowledge Base.
    Called by both Custom Resource CREATE and EventBridge scheduled events.
    
    Args:
        event: Lambda event (CloudFormation or EventBridge)
        context: Lambda context object
        is_custom_resource: Whether this is a Custom Resource invocation
        
    Returns:
        dict: Summary of operation (pages scraped, PDFs downloaded, ingestion status)
    """
    logger.info("=" * 80)
    logger.info("Starting scrape and sync operation")
    logger.info("=" * 80)
    
    result = {
        "pages_scraped": 0,
        "pdfs_downloaded": 0,
        "county_mappings_saved": 0,
        "ingestion_status": "NOT_STARTED"
    }
    
    try:
        # Step 1: Clear S3 bucket
        logger.info("Step 1: Clearing S3 bucket")
        clear_s3_bucket()
        logger.info("✓ S3 bucket cleared successfully")
        
        # Step 2: Scrape HTML pages
        logger.info("Step 2: Scraping HTML pages")
        pages_scraped = scrape_html_pages()
        result["pages_scraped"] = pages_scraped
        logger.info(f"✓ Scraped {pages_scraped} HTML pages")
        
        # Step 3: Discover and download PDFs
        logger.info("Step 3: Discovering and downloading PDFs")
        pdfs_downloaded, county_mappings_saved = discover_and_download_pdfs()
        result["pdfs_downloaded"] = pdfs_downloaded
        result["county_mappings_saved"] = county_mappings_saved
        logger.info(f"✓ Downloaded {pdfs_downloaded} PDF files, saved {county_mappings_saved} county mappings")
        
        # Step 4: Start Knowledge Base ingestion
        logger.info("Step 4: Starting Knowledge Base ingestion")
        success, job_id, data_source_id = start_kb_ingestion()
        
        if not success:
            logger.error("Failed to start ingestion job")
            result["ingestion_status"] = "FAILED_TO_START"
            return result
        
        logger.info(f"✓ Ingestion job started: {job_id}")
        result["ingestion_status"] = "STARTED"
        
        # Step 5: Wait for ingestion (with timeout awareness)
        remaining_time = get_remaining_time_seconds(context)
        logger.info(f"Step 5: Waiting for ingestion (remaining time: {remaining_time:.0f}s)")
        
        if remaining_time < LAMBDA_TIMEOUT_BUFFER:
            logger.warning(f"Not enough time to wait for ingestion ({remaining_time:.0f}s < {LAMBDA_TIMEOUT_BUFFER}s buffer)")
            logger.info("Ingestion job will complete asynchronously")
            result["ingestion_status"] = "TIMEOUT_GRACEFUL"
            return result
        
        ingestion_result = wait_for_ingestion(job_id, data_source_id, context)
        result["ingestion_status"] = ingestion_result["status"]
        
        if ingestion_result["status"] == "COMPLETE":
            logger.info("✓ Knowledge Base ingestion completed successfully")
        elif ingestion_result["status"] == "TIMEOUT_GRACEFUL":
            logger.info("✓ Ingestion started successfully, completing without waiting")
        else:
            logger.error(f"Ingestion ended with status: {ingestion_result['status']}")
        
        logger.info("=" * 80)
        logger.info("Scrape and sync operation completed")
        logger.info(f"Summary: {result}")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        error_msg = f"Error in scrape and sync: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        raise