import os
import logging

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Logging configuration - change LOG_LEVEL to control all modules
# Available levels: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL
LOG_LEVEL = logging.INFO  # Change this to control what gets logged
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
# CONSTANTS CONFIGURATION
# ============================================================================

API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL")
if not API_GATEWAY_URL:
    raise ValueError("API_GATEWAY_URL environment variable is required")


KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")
if not KNOWLEDGE_BASE_ID:
    raise ValueError("KNOWLEDGE_BASE_ID environment variable is required")

NUM_KB_RESULTS = os.environ.get("NUM_KB_RESULTS")
if not NUM_KB_RESULTS:
    raise ValueError("NUM_KB_RESULTS environment variable is required")

GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID")
if not GUARDRAIL_ID:
    raise ValueError("GUARDRAIL_ID environment variable is required")

GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION")
if not GUARDRAIL_VERSION:
    raise ValueError("GUARDRAIL_VERSION environment variable is required")

CONVERSATIONS_TABLE = os.environ.get("CONVERSATIONS_TABLE")
if not CONVERSATIONS_TABLE:
    raise ValueError("CONVERSATIONS_TABLE environment variable is required")

FOLLOWUP_TABLE = os.environ.get("FOLLOWUP_TABLE")
if not FOLLOWUP_TABLE:
    raise ValueError("FOLLOWUP_TABLE environment variable is required")

COUNTY_RESOURCES_TABLE = os.environ.get("COUNTY_RESOURCES_TABLE")
if not COUNTY_RESOURCES_TABLE:
    raise ValueError("COUNTY_RESOURCES_TABLE environment variable is required")

GUARDRAILS_CONFIG_STREAMING = {
        'guardrailIdentifier': GUARDRAIL_ID,
        'guardrailVersion': GUARDRAIL_VERSION,
        'trace': 'disabled',
        'streamProcessingMode': 'sync'
    }

GUARDRAILS_CONFIG = {
        'guardrailIdentifier': GUARDRAIL_ID,
        'guardrailVersion': GUARDRAIL_VERSION,
        'trace': 'disabled'
    }