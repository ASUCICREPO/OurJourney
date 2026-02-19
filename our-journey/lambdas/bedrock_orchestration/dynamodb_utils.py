import boto3
import logging
import traceback
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key
import json
import constants

logger = logging.getLogger(__name__)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
conversations_table = dynamodb.Table(constants.CONVERSATIONS_TABLE)
followup_table = dynamodb.Table(constants.FOLLOWUP_TABLE)
county_resources_table = dynamodb.Table(constants.COUNTY_RESOURCES_TABLE)


# ============================================================================
# CONVERSATION MANAGEMENT
# ============================================================================

def save_conversation(conversation_id, user_id, county, messages, user_info, 
                     flag='none', categories=None, last_message='', timestamp=None):
    """
    Save or update a conversation in DynamoDB.
    
    Args:
        conversation_id: Unique identifier for the conversation
        user_id: User identifier (can be email, phone, or generated ID)
        county: User's county/location
        messages: Full list of message objects [{"role": "user/assistant", "content": "..."}]
        user_info: Complete userInfo object
        flag: Status flag (none/crisis/followup/resolved)
        categories: List of conversation categories/topics
        last_message: The most recent message text
        timestamp: Optional timestamp to use (for updates). If not provided, creates new timestamp.
    """
    logger.info(f"Saving conversation: {conversation_id}")
    
    try:
        # Use provided timestamp or create new one
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
            logger.info(f"Created new timestamp: {timestamp}")
        else:
            logger.info(f"Using existing timestamp: {timestamp}")
        
        # Calculate message count
        message_count = len(messages)
        
        # Prepare categories
        if categories is None:
            categories = []
        
        # Prepare the item
        item = {
            'id': conversation_id,
            'timestamp': timestamp,
            'userId': user_id,
            'county': county,
            'messageCount': message_count,
            'lastMessage': last_message,
            'categories': categories,
            'flag': flag,
            'messages': messages,  # Full conversation history
            'userInfo': user_info,  # Store complete user info
            'updatedAt': datetime.utcnow().isoformat()  # Always update this
        }
        
        # Save to DynamoDB
        conversations_table.put_item(Item=item)
        
        logger.info(f"Conversation {conversation_id} saved successfully")
        return item
        
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


def update_conversation_flag(conversation_id, timestamp, new_flag):
    """
    Update the flag status of a conversation.
    
    Args:
        conversation_id: Unique identifier for the conversation
        timestamp: Timestamp of the conversation (sort key)
        new_flag: New flag value (none/crisis/followup/resolved)
    """
    logger.info(f"Updating conversation {conversation_id} flag to {new_flag}")
    
    try:
        conversations_table.update_item(
            Key={
                'id': conversation_id,
                'timestamp': timestamp
            },
            UpdateExpression='SET flag = :flag, updatedAt = :updated',
            ExpressionAttributeValues={
                ':flag': new_flag,
                ':updated': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Conversation flag updated successfully")
        
    except Exception as e:
        logger.error(f"Failed to update conversation flag: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


def get_conversation(conversation_id, timestamp):
    """
    Retrieve a conversation from DynamoDB.
    
    Args:
        conversation_id: Unique identifier for the conversation
        timestamp: Timestamp of the conversation (sort key)
    
    Returns:
        dict: Conversation item or None if not found
    """
    logger.info(f"Retrieving conversation: {conversation_id}")
    
    try:
        response = conversations_table.get_item(
            Key={
                'id': conversation_id,
                'timestamp': timestamp
            }
        )
        
        item = response.get('Item')
        if item:
            logger.info(f"Conversation {conversation_id} retrieved successfully")
        else:
            logger.warning(f"Conversation {conversation_id} not found")
        
        return item
        
    except Exception as e:
        logger.error(f"Failed to retrieve conversation: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


# ============================================================================
# FOLLOW-UP MANAGEMENT
# ============================================================================

def save_followup(conversation_id, user_id, county, email, phone, 
                 preferred_contact, conversation_summary, request_type='normal',
                 priority='normal', status='new'):
    """
    Save a follow-up request to DynamoDB.
    
    Args:
        conversation_id: Reference to the original conversation
        user_id: User identifier
        county: User's county/location
        email: User's email address (optional)
        phone: User's phone number (optional)
        preferred_contact: Preferred contact method ('email' or 'phone')
        conversation_summary: Summary of what the conversation was about
        request_type: Type of follow-up ('normal' or 'crisis')
        priority: Priority level ('normal' or 'urgent')
        status: Workflow status ('new', 'in-progress', 'completed')
    
    Returns:
        dict: The created follow-up item
    """
    logger.info(f"Saving follow-up for conversation: {conversation_id}")
    
    try:
        timestamp = datetime.utcnow().isoformat()
        followup_id = f"followup_{conversation_id}_{timestamp}"
        
        # Prepare the item
        item = {
            'id': followup_id,
            'timestamp': timestamp,
            'conversationId': conversation_id,
            'userId': user_id,
            'county': county,
            'status': status,
            'priority': priority,
            'requestType': request_type,
            'conversationSummary': conversation_summary,
            'createdAt': timestamp,
            'updatedAt': timestamp
        }
        
        # Add contact info if provided
        if email:
            item['email'] = email
        if phone:
            item['phone'] = phone
        if preferred_contact:
            item['preferredContact'] = preferred_contact
        
        # Save to DynamoDB
        followup_table.put_item(Item=item)
        
        logger.info(f"Follow-up {followup_id} saved successfully")
        return item
        
    except Exception as e:
        logger.error(f"Failed to save follow-up: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


def update_followup_status(followup_id, timestamp, new_status, assignee=None, notes=None):
    """
    Update the status of a follow-up request.
    
    Args:
        followup_id: Unique identifier for the follow-up
        timestamp: Timestamp of the follow-up (sort key)
        new_status: New status value ('new', 'in-progress', 'completed')
        assignee: Person assigned to handle the follow-up (optional)
        notes: Additional notes about the follow-up (optional)
    """
    logger.info(f"Updating follow-up {followup_id} status to {new_status}")
    
    try:
        update_expression = 'SET #status = :status, updatedAt = :updated'
        expression_values = {
            ':status': new_status,
            ':updated': datetime.utcnow().isoformat()
        }
        expression_names = {
            '#status': 'status'  # 'status' is a reserved word in DynamoDB
        }
        
        # Add assignee if provided
        if assignee:
            update_expression += ', assignedTo = :assignee'
            expression_values[':assignee'] = assignee
        
        # Add notes if provided
        if notes:
            update_expression += ', notes = :notes'
            expression_values[':notes'] = notes
        
        followup_table.update_item(
            Key={
                'id': followup_id,
                'timestamp': timestamp
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        
        logger.info(f"Follow-up status updated successfully")
        
    except Exception as e:
        logger.error(f"Failed to update follow-up status: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


def get_followup(followup_id, timestamp):
    """
    Retrieve a follow-up request from DynamoDB.
    
    Args:
        followup_id: Unique identifier for the follow-up
        timestamp: Timestamp of the follow-up (sort key)
    
    Returns:
        dict: Follow-up item or None if not found
    """
    logger.info(f"Retrieving follow-up: {followup_id}")
    
    try:
        response = followup_table.get_item(
            Key={
                'id': followup_id,
                'timestamp': timestamp
            }
        )
        
        item = response.get('Item')
        if item:
            logger.info(f"Follow-up {followup_id} retrieved successfully")
        else:
            logger.warning(f"Follow-up {followup_id} not found")
        
        return item
        
    except Exception as e:
        logger.error(f"Failed to retrieve follow-up: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_user_id(user_info):
    """
    Extract or generate a user ID from userInfo.
    Priority: email > phone > generated ID
    
    Args:
        user_info: User information dictionary
    
    Returns:
        str: User identifier
    """
    if user_info.get('email'):
        return user_info['email']
    elif user_info.get('phone'):
        return user_info['phone']
    else:
        # Generate a unique ID based on location and timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        location = user_info.get('location', 'unknown').replace(' ', '_').replace(',', '')
        return f"user_{location}_{timestamp}"


def extract_county(user_info):
    """
    Extract county from userInfo location field.
    
    Args:
        user_info: User information dictionary
    
    Returns:
        str: County name or 'Unknown'
    """
    location = user_info.get('location', '')
    if ',' in location:
        # Format is typically "Durham, NC" so take the first part
        return location.split(',')[0].strip()
    return location if location else 'Unknown'


def extract_categories(messages):
    """
    Extract conversation categories/topics from messages.
    This is a simple keyword-based extraction - can be enhanced with ML/LLM analysis.
    
    Args:
        messages: List of message objects
    
    Returns:
        list: List of category strings
    """
    categories = []
    
    # Keywords to look for in messages
    category_keywords = {
        'housing': ['housing', 'apartment', 'shelter', 'home', 'rent'],
        'employment': ['job', 'employment', 'work', 'career', 'interview'],
        'legal': ['legal', 'lawyer', 'court', 'attorney', 'law'],
        'health': ['health', 'medical', 'doctor', 'hospital', 'clinic'],
        'education': ['education', 'school', 'college', 'training', 'class'],
        'transportation': ['transportation', 'bus', 'ride', 'car', 'travel'],
        'family': ['family', 'children', 'kids', 'parent', 'child'],
        'financial': ['money', 'financial', 'budget', 'debt', 'income']
    }
    
    # Combine all message content
    all_text = ' '.join([
        msg.get('content', [{}])[0].get('text', '').lower() 
        if isinstance(msg.get('content'), list) 
        else msg.get('content', '').lower()
        for msg in messages
    ])
    
    # Check for keywords
    for category, keywords in category_keywords.items():
        if any(keyword in all_text for keyword in keywords):
            categories.append(category)
    
    return categories if categories else ['general']


def generate_conversation_summary(messages, max_length=200):
    """
    Generate a brief summary of the conversation.
    Takes the first user message as the primary topic.
    
    Args:
        messages: List of message objects
        max_length: Maximum length of summary
    
    Returns:
        str: Conversation summary
    """
    if not messages:
        return "No messages in conversation"
    
    # Find first user message
    for msg in messages:
        if msg.get('role') == 'user':
            content = msg.get('content', [{}])
            if isinstance(content, list) and content:
                text = content[0].get('text', '')
            else:
                text = str(content)
            
            # Truncate if too long
            if len(text) > max_length:
                return text[:max_length] + "..."
            return text
    
    return "Conversation summary unavailable"


def get_latest_conversation(conversation_id):
    """
    Get the most recent version of a conversation by ID.
    Queries DynamoDB to find the latest timestamp for this conversation.
    
    Args:
        conversation_id: Conversation identifier
    
    Returns:
        dict: Conversation object or None if not found
    """
    logger.info(f"Getting latest conversation: {conversation_id}")
    
    try:
        # Query to get latest version (most recent timestamp)
        response = conversations_table.query(
            KeyConditionExpression=Key('id').eq(conversation_id),
            ScanIndexForward=False,  # Sort descending (newest first)
            Limit=1
        )
        items = response.get('Items', [])
        item = items[0] if items else None
        
        if item:
            logger.info(f"Found latest conversation {conversation_id} with timestamp {item['timestamp']}")
        else:
            logger.info(f"No existing conversation found for {conversation_id}")
        
        return item
    
    except Exception as e:
        logger.error(f"Failed to get latest conversation: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


# ============================================================================
# COUNTY RESOURCES
# ============================================================================

def get_county_resource(county_name):
    """
    Retrieve the PDF resource mapping for a given NC county.
    Written by the scraper Lambda, read here to serve the PDF to the user.

    Args:
        county_name: County name exactly as stored by the scraper, e.g. "Wake" or "New Hanover"

    Returns:
        dict with keys 's3_key', 'source_url', 'last_updated' — or None if not found
    """
    logger.info(f"Looking up county resource for: {county_name}")

    try:
        response = county_resources_table.get_item(
            Key={"county": county_name}
        )

        item = response.get("Item")

        if item:
            logger.info(f"Found county resource for '{county_name}': {item.get('s3_key')}")
        else:
            logger.warning(f"No county resource found for '{county_name}'")

        return item

    except Exception as e:
        logger.error(f"Failed to retrieve county resource for '{county_name}': {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None