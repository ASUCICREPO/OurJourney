import logging
import boto3
from constants import (
    AWS_REGION, DOC_BUCKET_NAME,
    S3_DELETE_BATCH_SIZE,
    TEXT_FILE_SUFFIX, PDF_FILE_SUFFIX
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize AWS client
s3_client = boto3.client('s3', region_name=AWS_REGION)


# ============================================================================
# S3 OPERATIONS
# ============================================================================

def clear_s3_bucket():
    """
    Clear all objects from the document bucket.
    Deletes in batches to handle large numbers of files.
    """
    logger.info(f"Clearing bucket: {DOC_BUCKET_NAME}")
    
    try:
        # List all objects
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=DOC_BUCKET_NAME)
        
        delete_count = 0
        
        for page in pages:
            if 'Contents' not in page:
                continue
            
            # Prepare objects for deletion
            objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
            
            # Delete in batches
            for i in range(0, len(objects_to_delete), S3_DELETE_BATCH_SIZE):
                batch = objects_to_delete[i:i + S3_DELETE_BATCH_SIZE]
                
                response = s3_client.delete_objects(
                    Bucket=DOC_BUCKET_NAME,
                    Delete={'Objects': batch}
                )
                
                deleted = len(response.get('Deleted', []))
                delete_count += deleted
                logger.debug(f"Deleted batch of {deleted} objects")
        
        logger.info(f"Cleared {delete_count} objects from bucket")
        
    except Exception as e:
        error_msg = f"Error clearing S3 bucket: {str(e)}"
        logger.error(error_msg)
        raise


# ============================================================================
# S3 UPLOAD FUNCTIONS
# ============================================================================

def upload_text_to_s3(filename, text_content):
    """
    Upload text content to S3 bucket.
    
    Args:
        filename: Base filename (without extension)
        text_content: Text content to upload
    """
    key = f"{filename}{TEXT_FILE_SUFFIX}"
    
    s3_client.put_object(
        Bucket=DOC_BUCKET_NAME,
        Key=key,
        Body=text_content.encode('utf-8'),
        ContentType='text/plain'
    )
    
    logger.debug(f"Uploaded text file: {key}")


def upload_pdf_to_s3(filename, pdf_bytes):
    """
    Upload PDF content to S3 bucket.
    
    Args:
        filename: Filename (should include .pdf extension)
        pdf_bytes: PDF binary content
    """
    # Ensure filename has .pdf extension
    if not filename.endswith(PDF_FILE_SUFFIX):
        filename = f"{filename}{PDF_FILE_SUFFIX}"
    
    key = filename
    
    s3_client.put_object(
        Bucket=DOC_BUCKET_NAME,
        Key=key,
        Body=pdf_bytes,
        ContentType='application/pdf'
    )
    
    file_size_kb = len(pdf_bytes) / 1024
    logger.debug(f"Uploaded PDF: {key} ({file_size_kb:.1f} KB)")