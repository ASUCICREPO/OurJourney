import logging
import traceback
import time
import boto3
from constants import (
    AWS_REGION, KNOWLEDGE_BASE_ID,
    INGESTION_POLL_INTERVAL, INGESTION_MAX_WAIT_TIME,
    INGESTION_STATUS_STARTING, INGESTION_STATUS_IN_PROGRESS,
    INGESTION_STATUS_COMPLETE, INGESTION_STATUS_FAILED,
    LAMBDA_TIMEOUT_BUFFER
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize AWS client
bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)


# ============================================================================
# BEDROCK KNOWLEDGE BASE OPERATIONS
# ============================================================================

def start_kb_ingestion():
    """
    Start Knowledge Base ingestion job.
    
    Returns:
        tuple: (success: bool, job_id: str, data_source_id: str)
    """
    try:
        # Get data source ID
        data_source_id = get_data_source_id()
        logger.info(f"Data source ID: {data_source_id}")
        
        # Start ingestion job
        response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=data_source_id
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        logger.info(f"Started ingestion job: {job_id}")
        
        return True, job_id, data_source_id
        
    except Exception as e:
        logger.error(f"Error starting ingestion job: {str(e)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False, None, None


def get_data_source_id():
    """
    Get the data source ID for the Knowledge Base.
    
    Returns:
        str: Data source ID
    """
    try:
        response = bedrock_agent_client.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        data_sources = response.get('dataSourceSummaries', [])
        
        if not data_sources:
            raise ValueError(f"No data sources found for Knowledge Base: {KNOWLEDGE_BASE_ID}")
        
        # Return the first data source ID
        data_source_id = data_sources[0]['dataSourceId']
        return data_source_id
        
    except Exception as e:
        logger.error(f"Error getting data source ID: {str(e)}")
        raise


def wait_for_ingestion(job_id, data_source_id, context):
    """
    Wait for Knowledge Base ingestion job to complete.
    Polls status and checks for timeout.
    
    Args:
        job_id: Ingestion job ID
        data_source_id: Data source ID
        context: Lambda context for timeout checking
        
    Returns:
        dict: Ingestion result with status and details
    """
    logger.info(f"Waiting for ingestion job to complete: {job_id}")
    
    start_time = time.time()
    
    while True:
        try:
            # Check remaining Lambda time
            remaining_time = get_remaining_time_seconds(context)
            
            if remaining_time < LAMBDA_TIMEOUT_BUFFER:
                logger.warning(f"Approaching Lambda timeout ({remaining_time:.0f}s remaining)")
                logger.info("Returning gracefully - ingestion will complete asynchronously")
                return {
                    "status": "TIMEOUT_GRACEFUL",
                    "message": "Ingestion started but not completed within Lambda timeout"
                }
            
            # Check if we've exceeded max wait time
            elapsed_time = time.time() - start_time
            if elapsed_time > INGESTION_MAX_WAIT_TIME:
                logger.warning(f"Exceeded max wait time ({INGESTION_MAX_WAIT_TIME}s)")
                return {
                    "status": "TIMEOUT_GRACEFUL",
                    "message": "Ingestion started but exceeded max wait time"
                }
            
            # Get job status
            response = bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                dataSourceId=data_source_id,
                ingestionJobId=job_id
            )
            
            status = response['ingestionJob']['status']
            logger.debug(f"Ingestion status: {status} (elapsed: {elapsed_time:.0f}s)")
            
            if status == INGESTION_STATUS_COMPLETE:
                logger.info("Ingestion completed successfully")
                return {
                    "status": "COMPLETE",
                    "elapsed_time": elapsed_time
                }
            
            elif status == INGESTION_STATUS_FAILED:
                failure_reasons = response['ingestionJob'].get('failureReasons', [])
                logger.error(f"Ingestion failed: {failure_reasons}")
                return {
                    "status": "FAILED",
                    "failure_reasons": failure_reasons
                }
            
            elif status in [INGESTION_STATUS_STARTING, INGESTION_STATUS_IN_PROGRESS]:
                # Continue waiting
                time.sleep(INGESTION_POLL_INTERVAL)
            
            else:
                logger.warning(f"Unknown ingestion status: {status}")
                return {
                    "status": "UNKNOWN",
                    "raw_status": status
                }
        
        except Exception as e:
            logger.error(f"Error checking ingestion status: {str(e)}")
            raise


# ============================================================================
# UTILITY HELPERS
# ============================================================================

def get_remaining_time_seconds(context):
    """
    Get remaining Lambda execution time in seconds.
    
    Args:
        context: Lambda context object
        
    Returns:
        float: Remaining time in seconds
    """
    return context.get_remaining_time_in_millis() / 1000.0