import json
import logging
import traceback
from cfn_utils import (
    handle_create_request, handle_update_request, handle_delete_request,
    send_cfn_response
)
from orchestrator import scrape_and_sync
from constants import CFN_SUCCESS, RESPONSE_MESSAGES

import constants  # This configures logging

logger = logging.getLogger(__name__)


def lambda_handler(event, context):
    """
    Main entry point for OurJourney scraper Lambda function.
    
    Handles two execution modes:
    1. CloudFormation Custom Resource (Create/Update/Delete events)
    2. EventBridge scheduled events (weekly scraping)
    
    For Custom Resource mode:
    - CREATE: Scrapes websites and syncs Knowledge Base
    - UPDATE: No-op (weekly EventBridge handles updates)
    - DELETE: No-op (bucket has auto-delete policy)
    
    For EventBridge mode:
    - Scrapes websites and syncs Knowledge Base on schedule
    
    Args:
        event: Either CloudFormation event or EventBridge event
        context: Lambda context object with runtime information
        
    Returns:
        dict: Response for EventBridge mode, None for Custom Resource mode
    """
    logger.info("Starting OurJourney scraper Lambda handler")
    
    # Log the incoming event for debugging
    try:
        logger.debug("Event received:")
        logger.debug(json.dumps(event, indent=2))
    except Exception as e:
        logger.warning(f"Failed to log event data: {str(e)}")
    
    try:
        # Detect execution mode based on event structure
        request_type = event.get('RequestType')
        
        # ====================================================================
        # MODE 1: CloudFormation Custom Resource
        # ====================================================================
        if request_type:
            logger.info(f"Detected CloudFormation Custom Resource mode: {request_type}")
            
            # Route to appropriate handler based on request type
            if request_type == "Create":
                logger.info("Routing to Create request handler - will scrape and sync")
                handle_create_request(event, context)
                
            elif request_type == "Update":
                logger.info("Routing to Update request handler - no-op (EventBridge handles updates)")
                handle_update_request(event, context)
                
            elif request_type == "Delete":
                logger.info("Routing to Delete request handler - no-op (auto-delete enabled)")
                handle_delete_request(event, context)
                
            else:
                # Handle any unexpected request types gracefully
                logger.warning(f"Received unknown request type: {request_type}")
                success_message = f"{request_type} {RESPONSE_MESSAGES['GENERIC_SUCCESS']}"
                send_cfn_response(event, context, CFN_SUCCESS, {"Message": success_message})
        
        # ====================================================================
        # MODE 2: EventBridge Scheduled Event
        # ====================================================================
        else:
            logger.info("Detected EventBridge scheduled event mode")
            logger.info("Starting weekly scrape and sync operation")
            
            # Execute scraping and sync (no CloudFormation response needed)
            result = scrape_and_sync(event, context, is_custom_resource=False)
            
            logger.info("EventBridge scrape and sync completed successfully")
            return {
                "statusCode": 200,
                "body": json.dumps(result)
            }
    
    
    except KeyError as e:
        # Handle missing required fields in event
        error_msg = f"Missing required field in event: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Event structure: {json.dumps(event, default=str)}")
        
        # Only send CloudFormation response if this is a Custom Resource
        if event.get('RequestType'):
            try:
                send_cfn_response(event, context, CFN_SUCCESS, {"Error": error_msg})
            except Exception as response_error:
                logger.error(f"Failed to send error response to CloudFormation: {str(response_error)}")
        else:
            # EventBridge mode - just raise the error
            raise
    
    except Exception as e:
        # Catch-all error handler
        error_msg = f"Unexpected error in Lambda handler: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        # Only send CloudFormation response if this is a Custom Resource
        if event.get('RequestType'):
            try:
                send_cfn_response(event, context, CFN_SUCCESS, {"Error": error_msg})
            except Exception as response_error:
                logger.critical(f"Critical failure - cannot respond to CloudFormation: {str(response_error)}")
                logger.critical("CloudFormation stack may be stuck - manual intervention required")
        else:
            # EventBridge mode - let it fail and retry
            raise
    
    finally:
        logger.info("OurJourney scraper Lambda handler completed")