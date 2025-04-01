"""
ThinkingTool - Tool for processing cognitive tasks using LLM
"""

import json
from typing import Dict, Any, Optional

from .base import BaseTool
from ..config import config
from ..logger import logger


class ThinkingTool(BaseTool):
    """
    Tool for structured thinking and reasoning using LLM capabilities.

    This tool processes complex thinking tasks by leveraging the configured
    language model to generate structured responses.
    """

    @property
    def name(self) -> str:
        """Get the tool name."""
        return "think"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Process complex thinking tasks and generate structured reasoning"

    @property
    def parameters(self) -> Dict[str, Any]:
        """Get the tool parameters schema."""
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The thinking task or question to process",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context or background information for the task",
                    "optional": True,
                },
                "format": {
                    "type": "string",
                    "description": "Desired format for the response (e.g., 'json', 'markdown', 'text')",
                    "enum": ["json", "markdown", "text"],
                    "default": "text",
                },
            },
            "required": ["task"],
        }

    def __init__(self, **kwargs):
        """Initialize the thinking tool with optional configuration."""
        super().__init__(**kwargs)
        self.config = config
        self.llm = None  # Will be initialized on first use

    async def _get_llm(self):
        """Get or initialize the LLM client."""
        if not self.llm:
            # Initialize LLM based on configuration
            try:
                if self.config.llm.provider == "openai":
                    from app.llm.openai import OpenAIClient

                    self.llm = OpenAIClient(
                        api_key=self.config.llm.api_key,
                        model=self.config.llm.model,
                        temperature=self.config.llm.temperature,
                    )
                else:
                    raise ValueError(
                        f"Unsupported LLM provider: {self.config.llm.provider}"
                    )
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
                raise

        return self.llm

    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the thinking task using the configured LLM.

        Args:
            task: The thinking task or question to process
            context: Optional additional context
            format: Desired output format (default: 'text')

        Returns:
            Dictionary containing the processed results
        """
        task = kwargs.get("task")
        context = kwargs.get("context", "")
        output_format = kwargs.get("format", "text")

        if not task:
            return {"status": "error", "error": "No task provided"}

        try:
            llm = await self._get_llm()

            # Construct prompt with task and context
            prompt = f"Task: {task}\n"
            if context:
                prompt += f"\nContext: {context}\n"

            # Add format instructions
            if output_format == "json":
                prompt += "\nProvide your response in JSON format."
            elif output_format == "markdown":
                prompt += "\nFormat your response in Markdown."

            # Get response from LLM
            response = await llm.generate(prompt)

            # Process response based on format
            if output_format == "json":
                try:
                    result = json.loads(response)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON response, returning as text")
                    result = {"text": response}
            else:
                result = {"text": response}

            return {"status": "success", "result": result, "format": output_format}

        except Exception as e:
            logger.error(f"Error in thinking process: {e}")
            return {"status": "error", "error": str(e)}

    async def cleanup(self):
        """Clean up resources used by the thinking tool."""
        if self.llm:
            await self.llm.cleanup()
            self.llm = None

    async def reset(self):
        """Reset the thinking tool's state.

        This method resets the LLM client and any other internal state,
        allowing the tool to be reused with a fresh state.
        """
        if self.llm:
            await self.llm.cleanup()
            self.llm = None
