import json
import logging
import traceback
import uuid
from datetime import datetime
from chatbot_config import get_prompt, get_config, get_id
from utilities import (
    converse_with_model,
    parse_and_send_response,    
    execute_knowledge_base_query,
    format_results_for_response,
    send_to_gateway,
)
import dynamodb_utils
import followup_detector
import constants  # This configures logging

logger = logging.getLogger(__name__)


def apply_default_user_info(user_info):
    """
    Apply default values to userInfo fields if they are missing or empty.
    
    Args:
        user_info: Dictionary containing user information
        
    Returns:
        Dictionary with defaults applied for missing fields
    """
    # Hardcoded default values
    defaults = {
        "location": "Durham, NC",
        "releaseDate": "2024-01-15",
        "gender": "prefer_not_to_say",
        "over18": True,
        "language": "en"
    }
    
    # Create a copy to avoid modifying the original
    updated_info = user_info.copy()
    
    # Apply defaults for missing or empty fields
    for key, default_value in defaults.items():
        if key not in updated_info or updated_info[key] is None or updated_info[key] == "":
            updated_info[key] = default_value
            logger.debug(f"Applied default for {key}: {default_value}")
    
    return updated_info


# Orchestrate the chat request processing
def orchestrate(event):
    """
    Main orchestration function for processing chat requests via WebSocket.
    
    """
    logger.info("Starting orchestration")
    
    # Extract WebSocket connection ID
    try:
        connectionId = event["requestContext"]["connectionId"]
        logger.info(f"Processing connection: {connectionId}")
    except KeyError:
        logger.error("Failed to extract connection ID")
        return None
    
    
    try:
        # Parse request body
        body = json.loads(event["body"])
        chatHistory = body.get("messages", [])
        userInfo = body.get("userInfo", {})
        
        # Apply default values to userInfo
        userInfo = apply_default_user_info(userInfo)
        logger.info(f"User info after defaults: {userInfo}")
        
        # Get or generate conversation ID
        conversation_id = body.get("conversationId")
        if not conversation_id:
            # Generate new conversation ID if not provided
            conversation_id = f"conv_{uuid.uuid4().hex[:16]}"
            logger.info(f"Generated new conversation ID: {conversation_id}")
        else:
            logger.info(f"Using existing conversation ID: {conversation_id}")

        logger.info(f"Parsed {len(chatHistory)} messages")

        # Look up and send the county PDF resource before streaming the AI response
        # so the frontend can display a download button while the answer streams
        county = userInfo.get("county")
        if county:
            county_resource = dynamodb_utils.get_county_resource(county)
            if county_resource:
                send_to_gateway(connectionId, {
                    "type": "countyResource",
                    "data": {
                        "county": county_resource["county"],
                        "source_url": county_resource["source_url"],
                        "s3_key": county_resource["s3_key"],
                    }
                })
                logger.info(f"Sent county resource for '{county}' to client")
            else:
                logger.warning(f"No county resource available for '{county}' - skipping")
        else:
            logger.info("No county in userInfo - skipping county resource lookup")

        # Generate response
        response = respond_to_query(chatHistory=chatHistory, userInfo=userInfo)
        
        # Stream the response and capture the full assistant message
        # parse_and_send_response will be modified to return the captured text
        assistant_message = parse_and_send_response(response, connectionId, capture_text=True)
        
        # Add the assistant's response to chat history if we captured it
        if assistant_message:
            chatHistory.append({
                "role": "assistant",
                "content": [{"text": assistant_message}]
            })
            
            # Save conversation to DynamoDB
            save_conversation_to_db(
                conversation_id=conversation_id,
                chat_history=chatHistory,
                user_info=userInfo
            )
        
        logger.info("Answer processed and saved successfully")
              
    except Exception as e:
        logger.error(f"Orchestration failed: {str(e)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        
        if connectionId:
            parse_and_send_response("An unexpected error occurred. Please try again later.", 
                                  connectionId, classic=True, pure=True)
    
    logger.info("Orchestration completed")
    return None


# Respond to the user's query by orchestrating multiple stages.
def respond_to_query(chatHistory, userInfo):
    """
    Orchestrate the multi-stage pipeline to respond to  queries.
    """
    logger.info("Starting SQL query pipeline")
    
    try:

        
        specific_question = chatHistory[-1]['content'][-1].get('text', '') if chatHistory[-1].get('content') else ''

        # Stage 1: get answers from the database
        logger.info("Retrieving answers from the database")
        results = retrieve_answers_from_database(
            question=specific_question, 
            userInfo=userInfo
        )

        # Check if results are empty
        if not results:
            logger.warning("No results found for the specific question")
            results = "No results found for your query."

        # Format results for response
        results = format_results_for_response(specific_question, results)



        # Stage 3: Generate final response
        logger.info("Generating final response")
        final_response = get_final_response(
            chatHistory=chatHistory, 
            results=results,
            userInfo=userInfo
        )
        
        logger.info("pipeline completed")
        return final_response
        
    except Exception as e:
        logger.error(f"SQL pipeline failed: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


# Retrieve final response based on query results.
def get_final_response(chatHistory, results, userInfo):
    """
    Convert  query results into natural language response.
    Synthesizes data into conversational format that answers the user's question.
    """
    logger.info("Generating final response")
    
    try:

        response = converse_with_model(
            get_id(),
            chatHistory,
            config=get_config(),
            system=get_prompt(results=results, userInfo=userInfo),
            streaming=True
        )
        
        logger.info("Final response generated")
        return response
        
    except Exception as e:
        logger.error(f"Final response generation failed: {e}")
        raise


def retrieve_answers_from_database(question, userInfo):
    """
    Retrieve answers from the database based on the specific question.
    This function executes the SQL queries and returns the results. - All inside bedrock knowledge bases
    """
    logger.info("Retrieving answers from the database")
    
    # Convert userInfo to readable text, handling missing fields
    user_context_parts = []
    
    if userInfo.get('county'):
        user_context_parts.append(f"located in {userInfo['county']}")
    
    if userInfo.get('releaseDate'):
        user_context_parts.append(f"release date is {userInfo['releaseDate']}")
    
    if userInfo.get('age18Plus') is not None:
        age_status = "over 18" if userInfo['age18Plus'] else "under 18"
        user_context_parts.append(age_status)
    
    if userInfo.get('gender'):
        user_context_parts.append(f"gender is {userInfo['gender']}")
    
    if userInfo.get('email'):
        user_context_parts.append(f"email is {userInfo['email']}")
    
    if userInfo.get('phone'):
        user_context_parts.append(f"phone is {userInfo['phone']}")
    
    # Combine parts into a sentence, or use empty string if no user info
    if user_context_parts:
        user_context = f"User context: {', '.join(user_context_parts)}."
        query = f"{user_context}\n\nQuestion: {question}"
    else:
        query = question
    
    try:
        # Send question to the knowledge base
        results = execute_knowledge_base_query(query)
        logger.info("Database query executed successfully")
        return results
    except Exception as e:
        logger.error(f"Database retrieval failed: {e}")
        raise


def save_conversation_to_db(conversation_id, chat_history, user_info):
    """
    Save the conversation to DynamoDB and analyze for follow-up needs.
    
    Args:
        conversation_id: Unique conversation identifier
        chat_history: Full list of messages
        user_info: User information dictionary
    """
    logger.info(f"Saving conversation {conversation_id} to DynamoDB")
    
    try:
        # Extract user ID and county
        user_id = dynamodb_utils.extract_user_id(user_info)
        county = dynamodb_utils.extract_county(user_info)
        
        # Extract categories from conversation
        categories = dynamodb_utils.extract_categories(chat_history)
        
        # Get the last message
        last_message = ""
        if chat_history:
            last_msg = chat_history[-1]
            content = last_msg.get('content', [])
            if isinstance(content, list) and content:
                last_message = content[0].get('text', '')
            else:
                last_message = str(content)
        
        # Try to get existing conversation to reuse timestamp
        existing_conversation = dynamodb_utils.get_latest_conversation(conversation_id)
        
        if existing_conversation:
            # Reuse existing timestamp for updates
            timestamp = existing_conversation['timestamp']
            logger.info(f"Updating existing conversation with timestamp: {timestamp}")
        else:
            # Create new timestamp for first save
            timestamp = datetime.utcnow().isoformat()
            logger.info(f"Creating new conversation with timestamp: {timestamp}")
        
        # Save to DynamoDB with default flag 'none' initially
        saved_conversation = dynamodb_utils.save_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            county=county,
            messages=chat_history,
            user_info=user_info,
            flag='none',  # Default flag, will be updated if follow-up is needed
            categories=categories,
            last_message=last_message[:200],  # Truncate to 200 chars for preview
            timestamp=timestamp  # Pass timestamp to save function
        )
        
        logger.info(f"Conversation {conversation_id} saved successfully")
        
        # Get the user's message for follow-up analysis
        user_message = ""
        for msg in reversed(chat_history):
            if msg.get('role') == 'user':
                content = msg.get('content', [])
                if isinstance(content, list) and content:
                    user_message = content[0].get('text', '')
                else:
                    user_message = str(content)
                break
        
        # Analyze for follow-up needs
        if user_message:
            logger.info("Analyzing conversation for follow-up needs")
            followup_result = followup_detector.analyze_for_followup(
                user_message=user_message,
                user_info=user_info,
                conversation_id=conversation_id
            )
            
            # Process the follow-up result (update flags, create follow-up records)
            followup_detector.process_followup_result(
                followup_result=followup_result,
                conversation_id=conversation_id,
                timestamp=timestamp,  # Use the same timestamp
                user_info=user_info
            )
        
    except Exception as e:
        logger.error(f"Failed to save conversation to DB: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        # Don't raise - we don't want DB errors to break the user experience