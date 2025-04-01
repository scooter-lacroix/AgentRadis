#!/usr/bin/env python3
"""
Diagnostics script to understand the NoneType error in RadisProject
"""

import logging
import sys
import traceback

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def diagnose_llm_setup():
    """Diagnose LLM setup and configuration"""
    try:
        # Import core components
        from app.config import config
        from app.llm.llm import LMStudioLLM
        from app.llm.lm_studio_client import LMStudioClient
        from app.schema.models import Message
        
        # Check config
        logger.info(f"Active LLM: {config.active_llm}")
        logger.info(f"LLM Settings: {config.llm_settings}")
        
        # Initialize LMStudioLLM
        llm_config = config.get_llm_config().model_dump()
        llm = LMStudioLLM(llm_config)
        
        # Initialize LMStudioClient
        client = LMStudioClient(llm_config)
        
        # Test basic completion with debug tracing
        test_message = [Message(role="user", content="What is the meaning of life?")]
        
        # Trace through the client execution
        logger.debug("Testing LMStudioClient.create_chat_completion...")
        try:
            response, tools = client.create_chat_completion(test_message)
            logger.info(f"Client response: {response[:100]}...")
        except Exception as e:
            logger.error(f"Error in client.create_chat_completion: {e}")
            traceback.print_exc()
        
        # Test the LMStudioLLM directly
        logger.debug("Testing LMStudioLLM.complete...")
        try:
            raw_messages = [{"role": "user", "content": "What is the meaning of life?"}]
            response, metadata = llm.complete(raw_messages)
            logger.info(f"LLM response: {response[:100]}...")
            logger.info(f"Metadata: {metadata}")
        except Exception as e:
            logger.error(f"Error in llm.complete: {e}")
            traceback.print_exc()
            
        # Test the specific _create_chat_completion_sdk method which might have the issue
        logger.debug("Testing client._create_chat_completion_sdk...")
        try:
            response, tools = client._create_chat_completion_sdk(test_message)
            logger.info(f"SDK method response: {response[:100]}...")
        except Exception as e:
            logger.error(f"Error in _create_chat_completion_sdk: {e}")
            traceback.print_exc()
            
        return True
        
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Apply LMStudio patch first
    try:
        import lmstudio_patch
        logger.info("LMStudio patch applied")
    except ImportError:
        logger.warning("LMStudio patch not found, running without it")
    
    # Run diagnostics
    success = diagnose_llm_setup()
    sys.exit(0 if success else 1)
