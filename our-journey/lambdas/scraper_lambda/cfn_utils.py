import json
import logging
import traceback
import urllib3
from constants import CFN_SUCCESS, RESPONSE_MESSAGES
from orchestrator import scrape_and_sync

# Configure logging
logger = logging.getLogger(__name__)

# Initialize HTTP client for CloudFormation responses
http = urllib3.PoolManager()


# ============================================================================
# CLOUDFORMATION RESPONSE HANDLER
# ============================================================================

def send_cfn_response(event, context, response_status, response_data, physical_resource_id=None, no_echo=False, reason=None):
    """
    Send response back to CloudFormation service.
    Constructs and sends the required response format for CloudFormation
    custom resources using the pre-signed URL from the event.
    
    Args:
        event: CloudFormation event data containing ResponseURL
        context: Lambda context object
        response_status (str): SUCCESS or FAILED
        response_data (dict): Custom data to return
        physical_resource_id (str, optional): Resource identifier
        no_echo (bool, optional): Whether to mask the response
        reason (str, optional): Custom reason for the response
    """
    logger.info(f"Sending CloudFormation response: {response_status}")
    try:
        response_url = event['ResponseURL']
        response_body = {
            'Status': response_status,
            'Reason': reason or f"See CloudWatch Log Stream: {context.log_stream_name}",
            'PhysicalResourceId': physical_resource_id or context.log_stream_name,
            'StackId': event['StackId'],
            'RequestId': event['RequestId'],
            'LogicalResourceId': event['LogicalResourceId'],
            'NoEcho': no_echo,
            'Data': response_data
        }
        
        json_response_body = json.dumps(response_body)
        logger.debug(f"Response body: {json_response_body}")
        
        headers = {
            'content-type': '',
            'content-length': str(len(json_response_body))
        }
        
        response = http.request('PUT', response_url, headers=headers, body=json_response_body)
        logger.info(f"CloudFormation response sent successfully: {response.status}")
        
    except Exception as e:
        logger.error(f"Failed to send CloudFormation response: {str(e)}")
        # Don't re-raise - we don't want the Lambda to fail if CFN response fails


# ============================================================================
# CLOUDFORMATION EVENT HANDLERS
# ============================================================================

def handle_create_request(event, context):
    """
    Handle CloudFormation CREATE request.
    Executes full scrape and sync operation, then sends response to CloudFormation.
    """
    logger.info("Handling CREATE request - starting scrape and sync")
    
    try:
        # Execute the scraping and sync operation
        result = scrape_and_sync(event, context, is_custom_resource=True)
        
        # Send success response to CloudFormation
        logger.info("CREATE operation completed successfully")
        send_cfn_response(
            event, 
            context, 
            CFN_SUCCESS, 
            {
                "Message": RESPONSE_MESSAGES["CREATE_SUCCESS"],
                "PagesScraped": result.get("pages_scraped", 0),
                "PDFsDownloaded": result.get("pdfs_downloaded", 0),
                "CountyMappingsSaved": result.get("county_mappings_saved", 0),
                "IngestionStatus": result.get("ingestion_status", "UNKNOWN")
            }
        )
        
    except Exception as e:
        error_msg = f"CREATE request failed: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        # Send success anyway to prevent stack from hanging
        send_cfn_response(
            event,
            context,
            CFN_SUCCESS,
            {
                "Message": "CREATE completed with errors",
                "Error": error_msg
            }
        )


def handle_update_request(event, context):
    """
    Handle CloudFormation UPDATE request.
    No-op since weekly EventBridge schedule handles updates.
    """
    logger.info("Handling UPDATE request - no-op (EventBridge handles weekly updates)")
    
    send_cfn_response(
        event,
        context,
        CFN_SUCCESS,
        {
            "Message": RESPONSE_MESSAGES["UPDATE_SUCCESS"],
            "Note": "Weekly updates are handled by EventBridge schedule"
        }
    )


def handle_delete_request(event, context):
    """
    Handle CloudFormation DELETE request.
    No-op since S3 bucket has auto-delete enabled.
    """
    logger.info("Handling DELETE request - no-op (bucket has auto-delete policy)")
    
    send_cfn_response(
        event,
        context,
        CFN_SUCCESS,
        {
            "Message": RESPONSE_MESSAGES["DELETE_SUCCESS"],
            "Note": "S3 bucket has auto-delete policy enabled"
        }
    )