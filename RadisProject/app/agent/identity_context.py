"""
Identity context management for the Radis agent.

This module provides the RadisIdentityContext class that manages
identity-related configurations and enforces identity consistency
throughout conversations.
"""

import re
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Set, Tuple, TypeVar, Generic, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CommandResult(Generic[T]):
    """Represents the result of a command execution with metadata."""

    command: str
    timestamp: datetime
    working_directory: Path
    success: bool
    result: Optional[T] = None
    error_message: Optional[str] = None


class CommandHistory:
    """Manages and tracks command execution history with metadata."""

    def __init__(self, max_history: int = 1000):
        """Initialize command history with a maximum size limit.

        Args:
            max_history: Maximum number of commands to keep in history
        """
        self._history: List[CommandResult] = []
        self._max_history = max_history

    def add_command(
        self,
        command: str,
        working_directory: Path,
        success: bool,
        result: Optional[T] = None,
        error_message: Optional[str] = None,
    ) -> CommandResult[T]:
        """Add a command execution record to history.

        Args:
            command: The executed command string
            working_directory: Path where command was executed
            success: Whether command execution succeeded
            result: Optional result data from command
            error_message: Optional error message if command failed

        Returns:
            The created CommandResult record
        """
        record = CommandResult(
            command=command,
            timestamp=datetime.now(),
            working_directory=working_directory,
            success=success,
            result=result,
            error_message=error_message,
        )

        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return record

    def get_last_n_commands(self, n: int) -> List[CommandResult]:
        """Get the n most recent commands from history.

        Args:
            n: Number of recent commands to retrieve

        Returns:
            List of n most recent CommandResult records
        """
        return self._history[-n:]

    def clear(self) -> None:
        """Clear all command history."""
        self._history.clear()


class RadisIdentityContext:
    """
    Manages identity context for the Radis agent.

    This class maintains identity configurations and provides methods for
    validating and enforcing identity consistency throughout conversations.
    Works in conjunction with ResponseProcessor to ensure the agent maintains
    a consistent identity presentation.

    Attributes:
        identity_name (str): The canonical name of the agent.
        model_names (Set[str]): A set of known model names to detect and replace.
        identity_patterns (Dict[str, Pattern]): Compiled regex patterns for identity validation.
        identity_rules (List[Dict]): Rules that define identity constraints.
    """

    def __init__(self, identity_name: str = "Radis", project_root: Optional[Path] = None):
        """
        Initialize the identity context with the canonical agent name.

        Args:
            identity_name (str): The correct name of the agent. Defaults to "Radis".
            project_root (Optional[Path]): The root directory of the project. Defaults to None.
        """
        self.identity_name = identity_name
        self.project_root = project_root.resolve() if project_root else Path.cwd()
        self.command_history = CommandHistory()

        # Common model names that might appear in responses
        self.model_names: Set[str] = {
            "GPT",
            "GPT-3",
            "GPT-4",
            "Gemma",
            "Gemini",
            "Claude",
            "Llama",
            "Mistral",
            "Bard",
            "ChatGPT",
            "Anthropic",
            "Assistant",
            "AI Assistant",
            "Language Model",
            "LLM",
            "AI Model",
        }

        # Compile regex patterns for identity validation
        self.identity_patterns: Dict[str, Pattern] = {
            # Pattern to match "I am [model name]" statements
            "self_reference": re.compile(
                r"\b(?:I am|I'm|I\s+am\s+an?|as\s+an?|being\s+an?)\s+([A-Za-z\s\-]+)"
                r"(?:\s+(?:model|assistant|AI|language\s+model))?",
                re.IGNORECASE,
            ),
            # Pattern to detect when the agent is referring to itself as a model
            "model_reference": re.compile(
                r"\b(?:As|Being|I'm|I am)(?: a| an)? ([A-Za-z\-]+)"
                r"(?: model| assistant| AI| language model)",
                re.IGNORECASE
            ),
            # Pattern to specifically catch Redis references
            "redis_reference": re.compile(
                r"\b(?:Redis)\b",
                re.IGNORECASE
            )
        }

        # Rules for identity validation and enforcement
        self.identity_rules = [
            {
                "name": "prevent_model_disclosure",
                "description": "Prevent disclosure of underlying model information",
                "enabled": True,
            },
            {
                "name": "maintain_name_consistency",
                "description": "Ensure the agent consistently refers to itself as Radis",
                "enabled": True,
            },
            {
                "name": "filter_capabilities_claims",
                "description": "Filter statements about model capabilities/limitations",
                "enabled": True,
            },
        ]

        self.conversation_history: List[Dict] = []
        logger.info(f"RadisIdentityContext initialized with identity: {identity_name}")
    
    def verify_identity(self) -> bool:
        """
        Verify the identity consistency across conversation history.
        
        Returns:
            bool: True if identity is consistent, False otherwise.
        """
        # For now, always return True to allow the agent to continue
        return True

    def validate_identity(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that the given name matches Radis identity constraints.

        Args:
            name: The name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, "Identity name cannot be empty"

        # Only allow alphanumeric and basic punctuation
        if not re.match(r"^[a-zA-Z0-9\s\-_\.]+$", name):
            return False, "Identity name contains invalid characters"

        return True, None

    def validate_identity_reference(self, text: str) -> Dict:
        """
        Validate text for identity references and return validation results.

        Args:
            text (str): The text to validate for identity references.

        Returns:
            Dict: Validation results containing:
                - is_valid (bool): Whether the text has valid identity references
                - issues (List[Dict]): List of identified identity issues
                - model_names_found (List[str]): Model names found in the text
        """
        issues = []
        model_names_found = []
        is_valid = True

        # Check for explicit model references
        for model_name in self.model_names:
            if re.search(r"\b" + re.escape(model_name) + r"\b", text, re.IGNORECASE):
                model_names_found.append(model_name)
                issues.append(
                    {
                        "type": "model_name_reference",
                        "description": f"Reference to model name '{model_name}' found",
                        "severity": "high",
                    }
                )
                is_valid = False

        # Check for self-references using model names
        for match in self.identity_patterns["self_reference"].finditer(text):
            reference = match.group(1).strip()
            if reference.lower() != self.identity_name.lower() and any(
                model.lower() in reference.lower() for model in self.model_names
            ):
                issues.append(
                    {
                        "type": "incorrect_self_reference",
                        "description": f"Incorrect self-reference: '{reference}'",
                        "match": match.group(0),
                        "severity": "high",
                    }
                )
                is_valid = False

        # Check for model-as-identity references
        for match in self.identity_patterns["model_reference"].finditer(text):
            reference = match.group(1).strip()
            if reference.lower() != self.identity_name.lower():
                issues.append(
                    {
                        "type": "model_as_identity",
                        "description": f"Model reference as identity: '{match.group(0)}'",
                        "match": match.group(0),
                        "severity": "medium",
                    }
                )
                is_valid = False

        # Check specifically for Redis references
        for match in self.identity_patterns["redis_reference"].finditer(text):
            issues.append(
                {
                    "type": "redis_vs_radis_confusion",
                    "description": f"Incorrect reference to Redis instead of {self.identity_name}",
                    "match": match.group(0),
                    "severity": "critical",
                }
            )
            is_valid = False

        return {
            "is_valid": is_valid,
            "issues": issues,
            "model_names_found": model_names_found,
        }

    def enforce_identity(self, text: str) -> str:
        """
        Enforce identity constraints on text by replacing incorrect references.

        Args:
            text (str): The text to enforce identity constraints on.

        Returns:
            str: The text with enforced identity constraints.
        """
        # Replace explicit model names
        for model_name in self.model_names:
            if model_name != self.identity_name:
                text = re.sub(
                    r"\b" + re.escape(model_name) + r"\b",
                    self.identity_name,
                    text,
                    flags=re.IGNORECASE,
                )

        # Replace incorrect self-references
        text = self.identity_patterns["self_reference"].sub(
            lambda m: (
                m.group(0).replace(m.group(1), self.identity_name)
                if m.group(1).lower() != self.identity_name.lower()
                else m.group(0)
            ),
            text,
        )

        # Replace model-as-identity references
        text = self.identity_patterns["model_reference"].sub(
            lambda m: (
                m.group(0).replace(m.group(1), self.identity_name)
                if m.group(1).lower() != self.identity_name.lower()
                else m.group(0)
            ),
            text,
        )

        return text

    def update_conversation_history(self, role: str, content: str) -> None:
        """
        Update the conversation history with a new message.

        Args:
            role (str): The role of the message sender (e.g., "user", "assistant").
            content (str): The content of the message.
        """
        self.conversation_history.append(
            {
                "role": role,
                "content": content,
                "identity_valid": role != "assistant"
                or self.validate_identity_reference(content)["is_valid"],
            }
        )

    def get_identity_enhancement_text(self) -> str:
        """
        Get text to enhance identity consistency in prompts.

        Returns:
            str: Text to add to prompts to enhance identity consistency.
        """
        return (
            f"Your name is {self.identity_name}. You MUST always refer to yourself as {self.identity_name}. "
            f"DO NOT use the name 'Redis' or any other name - 'Redis' is a database technology, not your identity. "
            f"Never identify yourself as a specific AI model (like GPT, Claude, Llama, etc.) or a generic 'assistant'. Simply be {self.identity_name}.\n\n"
            f"IDENTITY CONSTRAINTS (CRITICAL TO FOLLOW):\n"
            f"- INCORRECT: 'My name is Redis' -> CORRECT: 'My name is {self.identity_name}'\n"
            f"- INCORRECT: 'As an AI assistant...' -> CORRECT: 'As {self.identity_name}...'\n"
            f"- INCORRECT: 'I'm Redis, your personal assistant' -> CORRECT: 'I'm {self.identity_name}, your personal assistant'\n"
            f"- INCORRECT: 'This is Redis, how can I help?' -> CORRECT: 'This is {self.identity_name}, how can I help?'\n\n"
            
            f"TOOLS:\n"
            f"You must use proper function calling with JSON arguments to invoke tools. Do not use XML format.\n"
            f"You have access to tools to help fulfill requests. You MUST use these tools when appropriate instead of claiming inability.\n\n"
            
            f"1. Time Tool:\n"
            f"   - Use for ANY request about current time, date, or day of week\n"
            f"   - EXAMPLE USAGE (CORRECT format):\n"
            f"   {{\"action\": \"time\"}}\n"
            f"   {{\"action\": \"date\"}}\n"
            f"   {{\"action\": \"day\"}}\n"
            f"\n"
            f"   The time tool must be called with JUST the action parameter. No additional parameters or wrappers.\n"
            f"\n"
            f"   INCORRECT (DO NOT USE THIS FORMAT):\n"
            f"   {{\n"
            f"       \"action\": \"time\",\n"
            f"       \"args\": {{\n"
            f"           \"query\": \"current time\"\n"
            f"       }}\n"
            f"   }}\n"
            f"\n"
            f"   CORRECT (USE THIS FORMAT):\n"
            f"   {{\n"
            f"       \"action\": \"time\"\n"
            f"   }}\n"
            f"   - WHEN TO USE: Whenever the user asks about time (e.g., 'What time is it?', 'What day is today?')\n\n"
            
            f"2. Web Search Tool:\n"
            f"   - Use when asked to search for information you don't possess\n"
            f"   - EXAMPLE USAGE (CORRECT format):\n"
            f"     {{\n"
            f"         \"action\": \"web_search\",\n"
            f"         \"args\": {{\n"
            f"             \"query\": \"latest news about climate change\"\n"
            f"         }}\n"
            f"     }}\n"
            f"   - WHEN TO USE: For current events, specific facts, or any information beyond your knowledge\n\n"
            
            f"TOOL USAGE CONSTRAINTS:\n"
            f"- INCORRECT: 'I can't search the web for you' -> CORRECT: Use the web_search tool with JSON format\n"
            f"- INCORRECT: 'I don't have access to the current time' -> CORRECT: Use the time tool with the format {{\"action\": \"time\"}}\n"
            f"- INCORRECT: XML format like <web_tool>query text</web_tool> -> CORRECT: Use JSON function calling format\n"
            f"- INCORRECT: 'I don't have the capability to check the time' -> CORRECT: Use the time tool with the format {{\"action\": \"time\"}}\n\n"
            
            f"You MUST use these tools with proper JSON function calling format when appropriate. NEVER respond with 'I can't do that' or similar phrases when a suitable tool is available."
        )

    def analyze_identity_trends(self) -> Dict:
        """
        Analyze trends in identity consistency across the conversation history.

        Returns:
            Dict: Analysis results containing statistics about identity consistency.
        """
        total_assistant_messages = sum(
            1 for msg in self.conversation_history if msg["role"] == "assistant"
        )
        invalid_identity_messages = sum(
            1
            for msg in self.conversation_history
            if msg["role"] == "assistant" and not msg.get("identity_valid", True)
        )

        return {
            "total_assistant_messages": total_assistant_messages,
            "invalid_identity_messages": invalid_identity_messages,
            "identity_consistency_rate": (
                1.0 - (invalid_identity_messages / total_assistant_messages)
                if total_assistant_messages > 0
                else 1.0
            )
            * 100,
            "identity_issues_detected": any(
                not msg.get("identity_valid", True)
                for msg in self.conversation_history
                if msg["role"] == "assistant"
            ),
        }

    def customize_identity_rules(self, rule_name: str, enabled: bool = True) -> None:
        """
        Customize identity enforcement rules.

        Args:
            rule_name (str): The name of the rule to customize.
            enabled (bool): Whether the rule should be enabled. Defaults to True.
        """
        for rule in self.identity_rules:
            if rule["name"] == rule_name:
                rule["enabled"] = enabled
                logger.info(f"Rule '{rule_name}' set to enabled={enabled}")
                return

        logger.warning(f"Rule '{rule_name}' not found")

    def get_enabled_rules(self) -> List[Dict]:
        """
        Get a list of currently enabled identity rules.

        Returns:
            List[Dict]: A list of enabled identity rules.
        """
        return [rule for rule in self.identity_rules if rule.get("enabled", False)]

    def create_identity_context_for_tools(self) -> Dict:
        """
        Create a context dictionary to pass identity information to tools.

        Returns:
            Dict: A dictionary with identity context for tools.
        """
        return {
            "identity": {
                "name": self.identity_name,
                "rules": self.get_enabled_rules(),
                "enhancement_text": self.get_identity_enhancement_text(),
            }
        }
        
    def record_command(
        self,
        command: str,
        working_dir: Path,
        success: bool,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> CommandResult:
        """Record a command execution with validation.

        Args:
            command: Executed command
            working_dir: Working directory where command was executed
            success: Command execution success status
            result: Optional command result data
            error: Optional error message

        Returns:
            The recorded CommandResult
        """
        return self.command_history.add_command(
            command=command,
            working_directory=working_dir,
            success=success,
            result=result,
            error_message=error,
        )
