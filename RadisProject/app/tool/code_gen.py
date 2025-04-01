from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    SQL = "sql"


@dataclass
class CodeGenResponse:
    code: str
    language: Language
    success: bool
    error: Optional[str] = None


class CodeGenTool:
    """Tool for generating code snippets based on templates."""
    
    def __init__(self):
        self.language_templates: Dict[Language, Dict[str, str]] = {
            Language.PYTHON: {
                "class": """class {name}:
    def __init__(self):
        pass""",
                "function": """def {name}({params}):
    pass""",
            },
            Language.JAVASCRIPT: {
                "class": """class {name} {
    constructor() {
    }
}""",
                "function": """function {name}({params}) {
}""",
            },
            Language.SQL: {
                "query": """SELECT {columns}
FROM {table}
WHERE {condition};""",
                "create_table": """CREATE TABLE {table} (
    {columns}
);""",
            },
        }

    @property
    def name(self) -> str:
        """The name of the tool."""
        return "code_gen"
        
    @property
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        return "Generates code snippets based on templates for different programming languages"
        
    @property
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": [lang.value for lang in Language],
                    "description": "The programming language to generate code for"
                },
                "template_type": {
                    "type": "string",
                    "description": "The type of template to use (e.g., 'class', 'function', 'query', 'create_table')"
                },
                "name": {
                    "type": "string",
                    "description": "Name for the class or function"
                },
                "params": {
                    "type": "string",
                    "description": "Parameters for the function, if applicable"
                },
                "columns": {
                    "type": "string",
                    "description": "Column names for SQL queries"
                },
                "table": {
                    "type": "string",
                    "description": "Table name for SQL queries"
                },
                "condition": {
                    "type": "string",
                    "description": "WHERE condition for SQL queries"
                }
            },
            "required": ["language", "template_type"]
        }

    async def run(self, **kwargs) -> Any:
        """
        Execute the code generation functionality.
        
        Args:
            language: String representing the language (python, javascript, sql)
            template_type: Type of template to use
            **kwargs: Additional parameters for template formatting
            
        Returns:
            Generated code as string
        """
        try:
            language_str = kwargs.get("language", "python")
            template_type = kwargs.get("template_type")
            
            # Convert string to Language enum
            language = next((lang for lang in Language if lang.value == language_str), Language.PYTHON)
            
            # Call the synchronous method
            response = self.generate_code(language, template_type, **kwargs)
            
            return response.code if response.success else f"Error: {response.error}"
        except Exception as e:
            return f"Error generating code: {str(e)}"

    def generate_code(
        self, language: Language, template_type: str, **kwargs
    ) -> CodeGenResponse:
        """
        Generate code using predefined templates for the specified language.
        """
        try:
            if language not in self.language_templates:
                raise ValueError(f"Unsupported language: {language}")

            templates = self.language_templates[language]
            if template_type not in templates:
                raise ValueError(f"Unknown template type: {template_type}")

            code = templates[template_type].format(**kwargs)
            return CodeGenResponse(code=code, language=language, success=True)
        except Exception as e:
            return CodeGenResponse(
                code="", language=language, success=False, error=str(e)
            )

    def analyze_code(self, code: str, language: Language) -> Dict[str, any]:
        """
        Analyze code and return metrics/information about it.
        """
        try:
            # Basic analysis - line count and character count
            lines = code.split("\n")
            analysis = {
                "line_count": len(lines),
                "char_count": len(code),
                "empty_lines": len([l for l in lines if not l.strip()]),
                "language": language.value,
                "success": True,
            }

            # Language-specific analysis
            if language == Language.PYTHON:
                analysis.update(
                    {
                        "class_count": len(
                            [l for l in lines if l.strip().startswith("class ")]
                        ),
                        "function_count": len(
                            [l for l in lines if l.strip().startswith("def ")]
                        ),
                    }
                )
            elif language == Language.JAVASCRIPT:
                analysis.update(
                    {
                        "class_count": len(
                            [l for l in lines if l.strip().startswith("class ")]
                        ),
                        "function_count": len(
                            [l for l in lines if l.strip().startswith("function ")]
                        ),
                    }
                )
            elif language == Language.SQL:
                analysis.update(
                    {
                        "query_type": self._detect_sql_query_type(code),
                    }
                )

            return analysis
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _detect_sql_query_type(self, sql_code: str) -> str:
        """
        Helper method to detect the type of SQL query.
        """
        sql_upper = sql_code.upper().strip()
        if sql_upper.startswith("SELECT"):
            return "SELECT"
        elif sql_upper.startswith("INSERT"):
            return "INSERT"
        elif sql_upper.startswith("UPDATE"):
            return "UPDATE"
        elif sql_upper.startswith("DELETE"):
            return "DELETE"
        elif sql_upper.startswith("CREATE"):
            return "CREATE"
        else:
            return "UNKNOWN"

    def get_supported_languages(self) -> List[Language]:
        """
        Return list of supported programming languages.
        """
        return list(Language)

    def get_available_templates(self, language: Language) -> List[str]:
        """
        Return available templates for the specified language.
        """
        if language not in self.language_templates:
            return []
        return list(self.language_templates[language].keys())
        
    def as_function(self) -> Dict[str, Any]:
        """Get the tool's schema in LLM function format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
        
    async def cleanup(self) -> None:
        """Clean up any resources used by the tool."""
        # No resources to clean up for this tool
        pass
        
    async def reset(self) -> None:
        """Reset the tool to its initial state."""
        # No state to reset for this tool
        pass
