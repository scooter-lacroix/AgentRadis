import re
import os
from pathlib import Path
from typing import List, Pattern, Optional


class ModelNameDetector:
    """Detects and sanitizes AI model name references in text content."""

    def __init__(self) -> None:
        """Initialize regex patterns for common AI model names."""
        self.patterns: List[Pattern] = [
            re.compile(r"\b(?:GPT-?[1-4]|GPT)\b", re.IGNORECASE),
            re.compile(r"\bClaude[- ]?(?:2|1\.?[0-9]|\d+)?\b", re.IGNORECASE),
            re.compile(r"\bLLaMA[- ]?(?:2|1|[1-2]\.?[0-9])?\b", re.IGNORECASE),
            re.compile(r"\bPalm[- ]?(?:2)?\b", re.IGNORECASE),
            re.compile(r"\bBard\b", re.IGNORECASE),
            re.compile(r"\bChatGPT\b", re.IGNORECASE),
            re.compile(r"\bDaVinci\b", re.IGNORECASE),
            re.compile(r"\bCodex\b", re.IGNORECASE),
        ]

    def replace_model_references(self, text: str) -> str:
        """
        Replace any detected AI model references with 'Radis'.

        Args:
            text: Input text that may contain model references

        Returns:
            Text with model references replaced by 'Radis'
        """
        if not text:
            return text

        result = text
        for pattern in self.patterns:
            result = pattern.sub("Radis", result)
        return result


class PathValidator:
    """Validates and sanitizes file paths within project boundaries."""

    def __init__(self, project_root: Optional[str] = None) -> None:
        """
        Initialize with project root directory.

        Args:
            project_root: Root directory to use as boundary. Defaults to current directory.
        """
        self.project_root = Path(project_root or os.getcwd()).resolve()

    def is_within_project(self, path: str) -> bool:
        """
        Check if a path is within project boundaries.

        Args:
            path: Path to validate

        Returns:
            True if path is within project boundaries, False otherwise
        """
        try:
            normalized_path = Path(path).resolve()
            return str(normalized_path).startswith(str(self.project_root))
        except (ValueError, OSError):
            return False

    def sanitize_path(self, path: str) -> str:
        """
        Sanitize a file path by resolving and validating it.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized absolute path

        Raises:
            ValueError: If path is outside project boundary or invalid
        """
        try:
            normalized_path = Path(path).resolve()
            if not self.is_within_project(str(normalized_path)):
                raise ValueError(f"Path {path} is outside project boundary")
            return str(normalized_path)
        except Exception as e:
            raise ValueError(f"Invalid path: {path}") from e


class ResponseProcessor:
    """Processes responses to ensure model name and path security."""

    def __init__(self, project_root: Optional[str] = None) -> None:
        """
        Initialize with model detector and path validator.

        Args:
            project_root: Root directory for path validation
        """
        self.model_detector = ModelNameDetector()
        self.path_validator = PathValidator(project_root)

    def process_response(self, response: str) -> str:
        """
        Process a response by sanitizing model references.

        Args:
            response: Text response to process

        Returns:
            Processed response with sanitized content
        """
        return self.model_detector.replace_model_references(response)

    def validate_path(self, path: str) -> str:
        """
        Validate and sanitize a file path.

        Args:
            path: Path to validate

        Returns:
            Sanitized path

        Raises:
            ValueError: If path is invalid or outside project boundary
        """
        return self.path_validator.sanitize_path(path)


import unittest


class TestResponseProcessor(unittest.TestCase):
    """Test cases for ResponseProcessor functionality."""

    def setUp(self) -> None:
        self.processor = ResponseProcessor()

    def test_model_name_detection(self) -> None:
        """Test detection and replacement of various model names."""
        test_cases = [
            ("I am GPT-4", "I am Radis"),
            ("Using Claude-2", "Using Radis"),
            ("LLaMA 2 model", "Radis model"),
            ("ChatGPT and GPT-3", "Radis and Radis"),
            ("Regular text", "Regular text"),
            ("CLAUDE is here", "Radis is here"),
            ("gpt response", "Radis response"),
        ]

        for input_text, expected in test_cases:
            self.assertEqual(
                self.processor.process_response(input_text),
                expected,
                f"Failed to properly replace model name in: {input_text}",
            )

    def test_path_validation(self) -> None:
        """Test path validation and sanitization."""
        test_root = os.getcwd()
        processor = ResponseProcessor(test_root)

        # Valid paths
        self.assertTrue(processor.validate_path("test.txt").endswith("test.txt"))

        # Invalid paths
        with self.assertRaises(ValueError):
            processor.validate_path("/etc/passwd")
        with self.assertRaises(ValueError):
            processor.validate_path("../outside_project.txt")

    def test_empty_input(self) -> None:
        """Test handling of empty inputs."""
        self.assertEqual(self.processor.process_response(""), "")
        with self.assertRaises(ValueError):
            self.processor.validate_path("")


if __name__ == "__main__":
    unittest.main()

import re
import os
from pathlib import Path
from typing import List, Optional, Pattern, Set, Tuple


class ResponseProcessor:
    """
    Processes and validates AI model responses to ensure security and identity compliance.

    This class handles:
    - Detection of model name references
    - Identity sanitization
    - Response validation
    - Path validation and security
    """

    def __init__(self, project_root: str):
        """
        Initialize the ResponseProcessor with security patterns and base directory.

        Args:
            project_root: The root directory path for the RadisProject
        """
        self.project_root = Path(project_root).resolve()

        # Regex patterns for model detection
        self.model_patterns: List[Pattern] = [
            re.compile(r"\b(gpt-4|gpt-3\.5-turbo)\b", re.IGNORECASE),
            re.compile(r"\bllama[-\s]?2\b", re.IGNORECASE),
            re.compile(r"\bclaude[-\s]?(2|1\.5)?\b", re.IGNORECASE),
            re.compile(r"\bpalm[-\s]?2\b", re.IGNORECASE),
        ]

        # Identity patterns
        self.identity_patterns: List[Pattern] = [
            re.compile(r"\b(I am|I\'m)\s+an?\s+AI\b", re.IGNORECASE),
            re.compile(r"\bas an AI( model| assistant)?\b", re.IGNORECASE),
        ]

        # Restricted directory names
        self.restricted_paths: Set[str] = {
            ".git",
            "node_modules",
            "__pycache__",
            "venv",
            "env",
            ".env",
            "temp",
            "tmp",
        }

    def detect_model_references(self, text: str) -> List[str]:
        """
        Detect any references to AI models in the text.

        Args:
            text: The text to analyze

        Returns:
            List of detected model references
        """
        references = []
        for pattern in self.model_patterns:
            matches = pattern.finditer(text)
            references.extend(match.group(0) for match in matches)
        return references

    def sanitize_identity(self, text: str) -> str:
        """
        Sanitize any AI self-references and ensure consistent identity.

        Args:
            text: The text to sanitize

        Returns:
            Sanitized text with consistent identity references
        """
        sanitized = text
        for pattern in self.identity_patterns:
            sanitized = pattern.sub("As Radis", sanitized)
        return sanitized

    def validate_response(self, response: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an AI response for security and compliance.

        Args:
            response: The response text to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not response or not isinstance(response, str):
            return False, "Invalid response format"

        # Check for potential command injection
        if re.search(r"[;&|`]", response):
            return False, "Response contains potentially unsafe characters"

        # Check for excessive length
        if len(response) > 50000:  # 50KB limit
            return False, "Response exceeds maximum allowed length"

        # Check for obvious security risk patterns
        security_patterns = [
            r"(rm|rmdir|dd)\s+-rf",  # Dangerous shell commands
            r"curl\s+.*?\|\s*sh",  # Shell piping
            r"wget\s+.*?\|\s*sh",  # Shell piping
            r"eval\(",  # Dangerous eval
            r"subprocess\.call",  # Direct subprocess calls
        ]

        for pattern in security_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return False, "Response contains potentially unsafe operations"

        return True, None

    def validate_path(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a file path for security and directory traversal prevention.

        Args:
            path: The path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Convert to absolute path and resolve any symlinks
            abs_path = Path(path).resolve()

            # Ensure path is within project root
            if not str(abs_path).startswith(str(self.project_root)):
                return False, "Path is outside project directory"

            # Check for restricted directories
            path_parts = abs_path.parts
            for part in path_parts:
                if part in self.restricted_paths:
                    return False, f"Access to {part} directory is restricted"

            # Check for directory traversal attempts
            if ".." in path_parts:
                return False, "Directory traversal detected"

            # Ensure path exists if it's meant to be read
            if not abs_path.exists() and not str(path).endswith(
                (".py", ".txt", ".json", ".yaml", ".yml")
            ):
                return False, "Invalid path or file type"

            return True, None

        except (ValueError, OSError) as e:
            return False, f"Path validation error: {str(e)}"


"""
Response processing utilities for sanitizing AI agent responses to maintain identity consistency.
"""

import re
from typing import List, Pattern, Tuple


class ResponseProcessor:
    """
    Processes AI agent responses to maintain consistent identity references.

    This class provides functionality to detect and sanitize incorrect self-references
    and model names in LLM responses, ensuring they consistently use "Radis" as the identity.
    """

    def __init__(self):
        """Initialize the ResponseProcessor with predefined patterns for identity detection."""
        # Patterns for common LLM self-references
        self._self_reference_patterns: List[Tuple[Pattern, str]] = [
            (
                re.compile(
                    r"\b(?:I am|I'm) (?:an AI|a language model|an assistant)\b",
                    re.IGNORECASE,
                ),
                "I am Radis",
            ),
            (
                re.compile(
                    r"\b(?:as an AI|as a language model|as an assistant)\b",
                    re.IGNORECASE,
                ),
                "as Radis",
            ),
        ]

        # Patterns for known model names and variants
        self._model_name_patterns: List[Tuple[Pattern, str]] = [
            (re.compile(r"\b(?:GPT-4|GPT-3\.5|GPT|ChatGPT)\b", re.IGNORECASE), "Radis"),
            (
                re.compile(r"\b(?:Gemma|Gemini|Bard|Claude|LLaMA)\b", re.IGNORECASE),
                "Radis",
            ),
            (
                re.compile(
                    r"\b(?:language model|AI assistant|AI model)\b", re.IGNORECASE
                ),
                "Radis",
            ),
        ]

    def sanitize_response(self, response: str) -> str:
        """
        Sanitize a response by replacing incorrect identity references with "Radis".

        Args:
            response: The raw response string to sanitize.

        Returns:
            The sanitized response with correct identity references.
        """
        sanitized = response

        # Replace self-references
        for pattern, replacement in self._self_reference_patterns:
            sanitized = pattern.sub(replacement, sanitized)

        # Replace model names
        for pattern, replacement in self._model_name_patterns:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    def detect_identity_violations(self, response: str) -> List[str]:
        """
        Detect all identity violations in a response.

        Args:
            response: The response string to check for violations.

        Returns:
            A list of detected identity violations.
        """
        violations = []

        # Check for self-references
        for pattern, _ in self._self_reference_patterns:
            matches = pattern.finditer(response)
            violations.extend(match.group(0) for match in matches)

        # Check for model names
        for pattern, _ in self._model_name_patterns:
            matches = pattern.finditer(response)
            violations.extend(match.group(0) for match in matches)

        return violations

    def contains_identity_violations(self, response: str) -> bool:
        """
        Check if a response contains any identity violations.

        Args:
            response: The response string to check.

        Returns:
            True if violations are found, False otherwise.
        """
        return len(self.detect_identity_violations(response)) > 0


# Unit tests
import unittest


class TestResponseProcessor(unittest.TestCase):
    """Unit tests for the ResponseProcessor class."""

    def setUp(self):
        self.processor = ResponseProcessor()

    def test_sanitize_self_references(self):
        """Test sanitization of AI self-references."""
        test_cases = [
            (
                "I am an AI language model trained to help you.",
                "I am Radis trained to help you.",
            ),
            (
                "As an AI assistant, I can help with that.",
                "As Radis, I can help with that.",
            ),
            (
                "I'm a language model designed to assist.",
                "I am Radis designed to assist.",
            ),
        ]

        for input_text, expected in test_cases:
            sanitized = self.processor.sanitize_response(input_text)
            self.assertEqual(sanitized, expected)

    def test_sanitize_model_names(self):
        """Test sanitization of specific model names."""
        test_cases = [
            ("GPT-4 can help you with that.", "Radis can help you with that."),
            (
                "This is similar to what Gemma would do.",
                "This is similar to what Radis would do.",
            ),
            ("ChatGPT and Bard are AI models.", "Radis and Radis are Radis."),
        ]

        for input_text, expected in test_cases:
            sanitized = self.processor.sanitize_response(input_text)
            self.assertEqual(sanitized, expected)

    def test_detect_violations(self):
        """Test detection of identity violations."""
        text = "I am an AI model like GPT-4 and Gemma."
        violations = self.processor.detect_identity_violations(text)

        self.assertEqual(len(violations), 3)
        self.assertTrue("I am an AI model" in violations)
        self.assertTrue("GPT-4" in violations)
        self.assertTrue("Gemma" in violations)

    def test_contains_violations(self):
        """Test boolean violation check."""
        self.assertTrue(
            self.processor.contains_identity_violations("I am an AI language model.")
        )
        self.assertFalse(
            self.processor.contains_identity_violations("I am Radis, here to help.")
        )


if __name__ == "__main__":
    unittest.main()
