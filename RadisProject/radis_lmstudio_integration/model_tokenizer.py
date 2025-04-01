import logging
from typing import Optional, Tuple, Dict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelTokenizer:
    """
    Handles token counting and model detection for LM Studio models.
    Uses tiktoken when available with fallback mechanisms.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the tokenizer with optional model name.
        Attempts to load tiktoken if available.
        
        Args:
            model_name: Optional name of the model to use for tokenization
        """
        self.model_name = model_name
        self.tiktoken_available = False
        self.encoder = None
        
        try:
            import tiktoken
            self.tiktoken_available = True
            if model_name:
                try:
                    self.encoder = tiktoken.encoding_for_model(model_name)
                    logger.info(f"Successfully initialized tiktoken encoder for model {model_name}")
                except KeyError:
                    logger.warning(f"Model {model_name} not found in tiktoken, using default encoder")
                    self.encoder = tiktoken.get_encoding("cl100k_base")
            else:
                self.encoder = tiktoken.get_encoding("cl100k_base")
                logger.info("Using default tiktoken encoder (cl100k_base)")
        except ImportError:
            logger.warning("tiktoken not available, falling back to approximate token counting")
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        Uses tiktoken if available, falls back to approximate counting.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            int: Number of tokens
        """
        if not text:
            return 0
            
        try:
            if self.tiktoken_available and self.encoder:
                return len(self.encoder.encode(text))
            else:
                # Fallback: approximate token count
                # This is a rough approximation: words + punctuation
                return len(text.split()) + text.count('.,!?;:()[]{}""\'\'')
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            # Fallback to basic approximation in case of error
            return len(text.split())
    
    def count_prompt_completion_tokens(self, prompt: str, completion: str) -> Tuple[int, int]:
        """
        Count tokens separately for prompt and completion.
        
        Args:
            prompt: The input prompt text
            completion: The completion/response text
            
        Returns:
            Tuple[int, int]: (prompt_tokens, completion_tokens)
        """
        prompt_tokens = self.count_tokens(prompt)
        completion_tokens = self.count_tokens(completion)
        return prompt_tokens, completion_tokens
    
    def detect_model(self, model_path: str) -> str:
        """
        Detect the model type from the model path or name.
        
        Args:
            model_path: Path to the model or model name
            
        Returns:
            str: Detected model type
        """
        model_path = model_path.lower()
        
        # Model detection patterns
        model_patterns: Dict[str, str] = {
            'llama': 'LlamaModel',
            'vicuna': 'Vicuna',
            'falcon': 'Falcon',
            'pythia': 'Pythia',
            'gpt': 'GPT',
            'mistral': 'Mistral',
            'mpt': 'MPT'
        }
        
        try:
            for pattern, model_type in model_patterns.items():
                if pattern in model_path:
                    logger.info(f"Detected model type: {model_type}")
                    return model_type
            
            logger.warning(f"Could not detect specific model type for: {model_path}")
            return "Unknown"
        except Exception as e:
            logger.error(f"Error during model detection: {str(e)}")
            return "Unknown"
    
    def get_token_limit(self, model_type: str) -> int:
        """
        Get the token limit for a specific model type.
        
        Args:
            model_type: The type of the model
            
        Returns:
            int: Maximum token limit for the model
        """
        token_limits = {
            'LlamaModel': 2048,
            'Vicuna': 2048,
            'Falcon': 2048,
            'Pythia': 2048,
            'GPT': 2048,
            'Mistral': 8192,
            'MPT': 2048,
            'Unknown': 2048
        }
        
        try:
            return token_limits.get(model_type, 2048)
        except Exception as e:
            logger.error(f"Error getting token limit: {str(e)}")
            return 2048  # Default fallback

