"""
Response Sanitizer Module

Handles sanitization and cleanup of model responses.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

class ResponseSanitizer:
    """
    Handles sanitization and cleanup of model responses.
    Provides methods to clean up and improve responses from language models.
    """
    
    @staticmethod
    def sanitize(text: str, model_name: Optional[str] = None) -> str:
        """
        Sanitizes the response text from the model.
        
        Args:
            text: The raw response text
            model_name: Optional model name for model-specific sanitization
            
        Returns:
            The sanitized text
        """
        if not text:
            return ""
        
        # Remove redundant newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove any potentially unsafe HTML/JS content
        text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
        
        # Clean up any markdown backtick code blocks without language
        text = re.sub(r'```\s+', '```\n', text)
        
        # Ensure proper spacing after headers
        text = re.sub(r'(#+)([^\n])', r'\1 \2', text)
        
        return text
    
    @staticmethod
    def extract_initial_response(text: str) -> str:
        """
        Extract just the initial response, removing any hallucinated chat continuations.
        Some models continue generating a fictional dialog after the response.
        
        Args:
            text: The raw response text
            
        Returns:
            The cleaned initial response
        """
        # Look for patterns that indicate the model is continuing the conversation
        continuation_patterns = [
            r'User:',
            r'Human:',
            r'Person:',
            r'Me:',
            r'You:',
            r'Assistant:',
            r'AI:',
            r'The assistant:',
        ]
        
        # Search for the earliest match of any pattern
        earliest_pos = len(text)
        
        for pattern in continuation_patterns:
            matches = list(re.finditer(f'\n{pattern}', text))
            if matches:
                # If first match is very early, it might be part of a quoted example
                # Only consider it if it's not within the first few characters
                for match in matches:
                    if match.start() > 10:  # Simple heuristic
                        earliest_pos = min(earliest_pos, match.start())
        
        # If we found a continuation, cut it off
        if earliest_pos < len(text):
            return text[:earliest_pos].strip()
        
        return text
