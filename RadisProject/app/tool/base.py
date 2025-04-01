import json
from abc import ABC, abstractmethod
from typing import Dict, Any

import jsonschema


class BaseTool(ABC):
    """Abstract base class for all tools in the Radis system.

    All tools must inherit from this class and implement the required methods.

    Attributes:
        name (str): The name of the tool, used for identification
        description (str): A human-readable description of what the tool does
        parameters (dict): JSON schema describing the tool's parameters
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        pass

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Execute the tool's main functionality.

        Args:
            **kwargs: Tool-specific parameters as defined in the parameters schema

        Returns:
            The result of the tool execution

        Raises:
            Any tool-specific exceptions
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up any resources used by the tool.

        This method is called after tool execution to perform any necessary cleanup.
        """
        pass

    @abstractmethod
    async def reset(self) -> None:
        """Reset the tool to its initial state.

        This method is called to reset any internal state between tool invocations.
        """
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against the tool's schema.

        Args:
            params: Dictionary of parameters to validate

        Returns:
            The validated parameters dictionary

        Raises:
            jsonschema.ValidationError: If parameters do not match the schema
        """
        jsonschema.validate(instance=params, schema=self.parameters)
        return params

    def get_schema(self) -> Dict[str, Any]:
        """Get the complete schema for the tool.

        Returns:
            A dictionary containing the tool's complete schema including name,
            description and parameters
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def as_function(self) -> Dict[str, Any]:
        """Get the tool's schema in LLM function format.

        Returns:
            A dictionary formatted for use as an OpenAI function definition
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
