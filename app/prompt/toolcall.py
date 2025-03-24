# Version: 1.0.0
# Updated on: 2023-10-01
# Description: Tool call prompts for agent execution.

SYSTEM_PROMPT = "You are an agent that can execute tool calls"

NEXT_STEP_PROMPT = (
    "If you want to stop interaction, use `terminate` tool/function call."
)

def format_tool_call(tool_name: str, **kwargs) -> str:
    """Format a tool call with the given tool name and parameters."""
    # Type checking can be added here for kwargs if needed
    return f"{tool_name}({', '.join(f'{key}={value}' for key, value in kwargs.items())})"

# Documentation for the prompts
def document_prompts() -> None:
    """Document the purpose and variables of each prompt."""
    print("SYSTEM_PROMPT: Instructions for using tools effectively.")
    print("NEXT_STEP_PROMPT: Guidance for determining the next action.")
    print("Variables: None specific to this prompt.")

# Tool-specific prompts
def get_tool_usage_prompt(tool_name: str) -> str:
    """Returns usage instructions for a specific tool."""
    return f"""
    Instructions for using the {tool_name} tool:
    - Ensure you provide all required parameters.
    - Follow the expected format: {tool_name}(param1=value1, param2=value2).
    - Check for any specific conditions or limitations of the tool.
    """

def get_error_recovery_prompt(tool_name: str) -> str:
    """Returns guidance for handling errors with a specific tool."""
    return f"""
    If the {tool_name} tool fails:
    - Review the error message for clues.
    - Validate your inputs and try again.
    - If the issue persists, consider alternative tools or methods.
    """
