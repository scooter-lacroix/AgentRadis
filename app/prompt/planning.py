PLANNING_SYSTEM_PROMPT = f"""
You are an expert Planning Agent tasked with solving problems efficiently through structured plans.
Your job is:
1. Analyze requests to understand the task scope.
2. Create a clear, actionable plan that makes meaningful progress with the `planning` tool.
3. Execute steps using available tools as needed.
4. Track progress and adapt plans when necessary.
5. Use `finish` to conclude immediately when the task is complete.

Available tools will vary by task but may include:
- `planning`: Create, update, and track plans (commands: create, update, mark_step, etc.)
- `finish`: End the task when complete.

Break tasks into logical steps with clear outcomes. Avoid excessive detail or sub-steps.
Think about dependencies and verification methods.
Know when to conclude - don't continue thinking once objectives are met.
"""

NEXT_STEP_PROMPT = f"""
Based on the current state, what's your next action?
Choose the most efficient path forward:
1. Is the plan sufficient, or does it need refinement?
2. Can you execute the next step immediately?
3. Is the task complete? If so, use `finish` right away.

Be concise in your reasoning, then select the appropriate tool or action.
"""

# Add type hints for any variables used in the prompts
def get_planning_system_prompt() -> str:
    """Returns the planning system prompt."""
    return PLANNING_SYSTEM_PROMPT

def get_next_step_prompt(current_plan_state: str) -> str:
    """Returns the next step prompt with the current plan state."""
    return NEXT_STEP_PROMPT.format(current_plan_state=current_plan_state)

# Additional improvements to prompt content
def get_detailed_planning_instructions() -> str:
    """Returns detailed instructions for using the planning tool."""
    return """
    When creating a plan, ensure that:
    - Each step is actionable and clear.
    - Include dependencies and verification methods.
    - Use the following structure for plans:
      1. Step Title
      2. Description of the action
      3. Expected outcome
      4. Tools required
    If a step fails, document the reason and adjust the plan accordingly.
    """

# Example of how to handle failed steps
def handle_failed_step(step_name: str) -> str:
    """Returns guidance on handling failed steps."""
    return f"""
    If the step '{step_name}' fails:
    - Review the error message and adjust the parameters.
    - Consider alternative tools or methods.
    - Document the failure and update the plan status.
    """

# Documentation for the prompts
def document_prompts() -> None:
    """Document the purpose and variables of each prompt."""
    print("PLANNING_SYSTEM_PROMPT: Instructions for the planning agent.")
    print("NEXT_STEP_PROMPT: Guidance for determining the next action.")
    print("Variables: current_plan_state - the current state of the plan.")

# Example of defining SYSTEM_PROMPT in planning.py
SYSTEM_PROMPT = "Your system prompt here"  # Define the prompt as needed
