import logging
import time
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class LMStudioError(Exception):
    """Base exception class for LM Studio errors"""
    pass

class LMStudioConnectionError(LMStudioError):
    """Raised when connection to LM Studio server fails"""
    pass

class LMStudioModelError(LMStudioError):
    """Raised when there are issues with the model loading or availability"""
    pass

class LMStudioRequestError(LMStudioError):
    """Raised when the request to LM Studio is invalid"""
    pass

class LMStudioResponseError(LMStudioError):
    """Raised when response from LM Studio is invalid or cannot be parsed"""
    pass

class ModelStatus(Enum):
    LOADED = "loaded"
    UNLOADED = "unloaded"
    UNKNOWN = "unknown"

@dataclass
class LMStudioConfig:
    """Configuration for LM Studio client"""
    api_base: str = "http://127.0.0.1:1234"
    api_version: str = "v1"
    default_model: str = "default"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 60

class LMStudioBaseClient:
    """Base class for LM Studio clients with common functionality"""
    
    def __init__(
        self,
        config: Optional[LMStudioConfig] = None,
        **kwargs
    ):
        self.config = config or LMStudioConfig(**kwargs)
        self._last_health_check = 0
        self._health_status = False

    @property
    def chat_completions_url(self) -> str:
        """Get the chat completions endpoint URL"""
        return f"{self.config.api_base}/{self.config.api_version}/chat/completions"

    @property
    def models_url(self) -> str:
        """Get the models endpoint URL"""
        return f"{self.config.api_base}/{self.config.api_version}/models"

    def _check_api_health(self, force: bool = False) -> bool:
        """Check if the API is healthy and responding"""
        current_time = time.time()
        if not force and current_time - self._last_health_check < self.config.health_check_interval:
            return self._health_status

        try:
            response = requests.get(
                f"{self.config.api_base}/health",
                timeout=self.config.timeout
            )
            self._health_status = response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {str(e)}")
            self._health_status = False

        self._last_health_check = current_time
        return self._health_status

    def _verify_model_loaded(self, model_name: str) -> ModelStatus:
        """Verify if the specified model is loaded and available"""
        try:
            response = requests.get(
                self.models_url,
                timeout=self.config.timeout
            )
            if response.status_code != 200:
                return ModelStatus.UNKNOWN

            models_data = response.json()
            for model in models_data.get("data", []):
                if model.get("id") == model_name:
                    return ModelStatus.LOADED
            return ModelStatus.UNLOADED

        except requests.exceptions.RequestException as e:
            logger.error(f"Model verification failed: {str(e)}")
            return ModelStatus.UNKNOWN

    def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic"""
        if not self._check_api_health():
            raise LMStudioConnectionError("LM Studio API is not healthy")

        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code >= 500 and retry_count < self.config.max_retries:
                time.sleep(self.config.retry_delay * (retry_count + 1))
                return self._make_request(method, url, data, retry_count + 1)

            error_msg = f"Request failed with status {response.status_code}"
            try:
                error_data = response.json()
                error_msg = f"{error_msg}: {error_data.get('error', {}).get('message', 'Unknown error')}"
            except ValueError:
                error_msg = f"{error_msg}: {response.text}"

            raise LMStudioRequestError(error_msg)

        except requests.exceptions.RequestException as e:
            raise LMStudioConnectionError(f"Failed to connect to LM Studio: {str(e)}")

    def validate_messages(self, messages: List[Dict[str, str]]) -> None:
        """Validate chat messages format"""
        if not messages:
            raise LMStudioRequestError("Messages list cannot be empty")

        required_fields = {"role", "content"}
        valid_roles = {"system", "user", "assistant"}

        for msg in messages:
            missing_fields = required_fields - set(msg.keys())
            if missing_fields:
                raise LMStudioRequestError(f"Message missing required fields: {missing_fields}")
            
            if msg["role"] not in valid_roles:
                raise LMStudioRequestError(f"Invalid role: {msg['role']}. Must be one of {valid_roles}")

    def prepare_chat_request(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Prepare a chat completion request payload"""
        self.validate_messages(messages)
        
        return {
            "model": model or self.config.default_model,
            "messages": messages,
            "stream": False,
            **kwargs
        }

