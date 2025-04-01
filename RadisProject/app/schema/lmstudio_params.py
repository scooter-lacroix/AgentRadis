"""
Parameter models for LM Studio API requests.

This module defines structured parameter classes for LM Studio API calls.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class GenerateParams(BaseModel):
    """
    Parameters for the completions/generate endpoint in LM Studio.
    
    This class provides a structured way to pass parameters to the
    remote_call("completions/generate", ...) function while ensuring
    proper error handling and serialization.
    """
    prompt: str = Field(..., description="The prompt to generate completions for")
    max_tokens: Optional[int] = Field(default=1024, description="Maximum number of tokens to generate")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature")
    top_p: Optional[float] = Field(default=0.95, description="Nucleus sampling parameter")
    top_k: Optional[int] = Field(default=40, description="Top-k sampling parameter")
    stop: Optional[Union[str, List[str]]] = Field(default=None, description="Sequences to stop generation at")
    frequency_penalty: Optional[float] = Field(default=0.0, description="Penalty for token frequency")
    presence_penalty: Optional[float] = Field(default=0.0, description="Penalty for token presence")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the parameters to a dictionary suitable for the remote_call function.
        
        Returns:
            Dict[str, Any]: Dictionary with all non-None parameters.
        """
        # Convert to dict and filter out None values
        result = {k: v for k, v in self.model_dump().items() if v is not None}
        return result


class HealthCheckParams(BaseModel):
    """
    Parameters for checking LM Studio server health.
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the parameters to a dictionary suitable for the remote_call function.
        
        Returns:
            Dict[str, Any]: Empty dictionary as health check doesn't need parameters.
        """
        return {}
