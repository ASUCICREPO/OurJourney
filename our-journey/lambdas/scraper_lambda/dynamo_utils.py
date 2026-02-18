import logging
import traceback
from datetime import datetime
import boto3
from constants import AWS_REGION, COUNTY_RESOURCES_TABLE_NAME

# Configure logging
logger = logging.getLogger(__name__)

# Initialize AWS client
dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)


# ============================================================================
# DYNAMODB OPERATIONS
# ============================================================================

def upsert_county_pdf(county_name, s3_key, source_url):
    """
    Write or overwrite the county -> PDF mapping in DynamoDB.
    Called once per PDF after a successful S3 upload.

    Args:
        county_name: Human-readable county name, e.g. "Wake" or "New Hanover"
        s3_key:      S3 object key the PDF was uploaded as, e.g. "wake.pdf"
        source_url:  Canonical ourjourney2gether.com URL the PDF was linked from

    Returns:
        bool: True on success, False on failure
    """
    county_normalized = county_name.strip()

    try:
        dynamodb_client.put_item(
            TableName=COUNTY_RESOURCES_TABLE_NAME,
            Item={
                "county":      {"S": county_normalized},
                "s3_key":      {"S": s3_key},
                "source_url":  {"S": source_url},
                "last_updated": {"S": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")},
            }
        )
        logger.debug(f"Upserted DynamoDB record: {county_normalized} -> {s3_key}")
        return True

    except Exception as e:
        logger.error(f"Failed to upsert county record for '{county_normalized}': {str(e)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False