import logging
from prompts import prompt
import constants  # This configures logging
import random
import json

logger = logging.getLogger(__name__)


# ============================================================================
# MODEL ID DEFINITIONS
# ============================================================================

# Model ID
model_id = "us.amazon.nova-pro-v1:0"


# ============================================================================
# TEMPERATURE DEFINITIONS
# ============================================================================

# Default temperature
temperature = 0.3

# ============================================================================
# RETRIEVAL FUNCTIONS
# ============================================================================

# This function retrieves the appropriate prompt based on the type of interaction.
def get_prompt(results=None, userInfo=None):
    """
    Returns the appropriate prompt based on the specified type.
    Formats prompts with provided parameters for AI model consumption.
    """
    logger.info(f"Getting prompt")
    
    try:
        # Extract the language preference from userInfo (dropdown selection)
        user_language = (userInfo or {}).get("language", "en")
        
        # Remove the 'language' field from userInfo before injecting into the general user context
        # It will be passed separately as a dedicated language instruction
        prompt_user_info = {k: v for k, v in (userInfo or {}).items() if k != "language"}
        
        return [
            {
                "text": prompt.prompt.format(
                    results=results,
                    userInfo=json.dumps(prompt_user_info),
                    preferredLanguage=user_language
                ), 
            }
        ]
        
    except Exception as e:
        logger.error(f"Failed to get prompt: {e}")
        raise


# This function retrieves the configuration settings based on the type of interaction.
def get_config():
    """
    Returns configuration settings based on the specified type.
    Provides temperature and other model parameters for different use cases.
    """
    logger.info(f"Getting config")
    
    try:
        return {
            "temperature": temperature,
        }
        
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise


# This function retrieves the appropriate model ID based on the type of interaction.
def get_id():
    """
    Returns the appropriate model ID based on the specified type.
    Maps interaction types to their corresponding AI models.
    """
    logger.info(f"Getting model ID")
    
    try:
        return model_id
        
    except Exception as e:
        logger.error(f"Failed to get model ID: {e}")
        raise