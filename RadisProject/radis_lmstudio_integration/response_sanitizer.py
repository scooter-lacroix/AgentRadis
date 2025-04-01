import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional, Tuple, Union

class ResponseSanitizer:
    """Handles sanitization and validation of model responses."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the ResponseSanitizer with optional custom logger."""
        self.logger = logger or logging.getLogger(__name__)
        
        # Common patterns to clean up
        self._common_artifacts = [
            (r'```[a-zA-Z]*\n', ''),  # Remove code block markers
            (r'```\n?$', ''),         # Remove trailing code block marker
            (r'^\s*<\|.*?\|>\s*', ''),  # Remove special tokens
            (r'\r\n', '\n'),          # Normalize line endings
        ]
        
    def clean_response(self, response: str) -> str:
        """
        Clean the response by removing common artifacts and normalizing content.
        
        Args:
            response: Raw response string from the model
            
        Returns:
            Cleaned response string
        """
        try:
            # Remove null bytes and normalize whitespace
            cleaned = response.replace('\0', '').strip()
            
            # Apply common cleanup patterns
            for pattern, replacement in self._common_artifacts:
                cleaned = re.sub(pattern, replacement, cleaned)
                
            return cleaned
        except Exception as e:
            self.logger.error(f"Error cleaning response: {str(e)}")
            return response
            
    def validate_json(self, content: str) -> Tuple[bool, Optional[dict]]:
        """
        Validate and attempt to fix JSON content.
        
        Args:
            content: String containing potential JSON content
            
        Returns:
            Tuple of (is_valid, parsed_json)
        """
        try:
            # First try direct parsing
            parsed = json.loads(content)
            return True, parsed
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON detected: {str(e)}")
            
            try:
                # Attempt to fix common JSON issues
                fixed_content = content
                # Fix missing quotes around keys
                fixed_content = re.sub(r'(\w+)(?=\s*:)', r'"\1"', fixed_content)
                # Fix single quotes to double quotes
                fixed_content = fixed_content.replace("'", '"')
                # Fix trailing commas
                fixed_content = re.sub(r',(\s*[}\]])', r'\1', fixed_content)
                
                parsed = json.loads(fixed_content)
                self.logger.info("Successfully fixed and parsed JSON")
                return True, parsed
            except json.JSONDecodeError:
                self.logger.error("Failed to fix JSON content")
                return False, None

    def validate_xml(self, content: str) -> Tuple[bool, Optional[ET.Element]]:
        """
        Validate and attempt to fix XML content.
        
        Args:
            content: String containing potential XML content
            
        Returns:
            Tuple of (is_valid, parsed_xml)
        """
        try:
            # First try direct parsing
            root = ET.fromstring(content)
            return True, root
        except ET.ParseError as e:
            self.logger.warning(f"Invalid XML detected: {str(e)}")
            
            try:
                # Attempt to fix common XML issues
                fixed_content = content
                # Fix unclosed tags
                unclosed_tags = re.findall(r'<(\w+)[^>]*>[^<]*(?![^<]*</\1>)', fixed_content)
                for tag in unclosed_tags:
                    fixed_content = fixed_content + f"</{tag}>"
                
                root = ET.fromstring(fixed_content)
                self.logger.info("Successfully fixed and parsed XML")
                return True, root
            except ET.ParseError:
                self.logger.error("Failed to fix XML content")
                return False, None

    def sanitize_special_chars(self, content: str) -> str:
        """
        Handle special characters and formatting in the content.
        
        Args:
            content: String to sanitize
            
        Returns:
            Sanitized string
        """
        try:
            # Remove control characters except newlines and tabs
            cleaned = ''.join(char for char in content if char == '\n' or char == '\t' or char >= ' ')
            
            # Normalize unicode characters
            cleaned = cleaned.encode('ascii', 'ignore').decode('ascii')
            
            # Remove excessive whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            return cleaned
        except Exception as e:
            self.logger.error(f"Error sanitizing special characters: {str(e)}")
            return content

    def process_response(self, 
                        response: str, 
                        expected_format: Optional[str] = None) -> Union[str, dict, ET.Element, None]:
        """
        Process and validate a model response based on expected format.
        
        Args:
            response: Raw response string from the model
            expected_format: Optional format specification ('json', 'xml', or None)
            
        Returns:
            Processed and validated response in the appropriate format
        """
        try:
            # Initial cleaning
            cleaned_response = self.clean_response(response)
            
            if expected_format == 'json':
                is_valid, processed = self.validate_json(cleaned_response)
                if is_valid:
                    return processed
                self.logger.error("Failed to process JSON response")
                return None
                
            elif expected_format == 'xml':
                is_valid, processed = self.validate_xml(cleaned_response)
                if is_valid:
                    return processed
                self.logger.error("Failed to process XML response")
                return None
                
            else:
                # For plain text, just clean special characters
                return self.sanitize_special_chars(cleaned_response)
                
        except Exception as e:
            self.logger.error(f"Error processing response: {str(e)}")
            return None

