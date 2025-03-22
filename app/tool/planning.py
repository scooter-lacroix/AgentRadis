# tool/planning.py
import json
import logging
from typing import Dict, Any, List, Optional, Union
import asyncio

from app.tool.base import BaseTool
from app.logger import logger


_PLANNING_TOOL_DESCRIPTION = """
A planning tool that allows the agent to create and manage plans for solving complex tasks.
The tool provides functionality for creating plans, updating plan steps, and tracking progress.
"""


class PlanningTool(BaseTool):
    """
    A planning tool that allows the agent to create and manage plans for solving complex tasks.
    The tool provides functionality for creating plans, updating plan steps, and tracking progress.
    """

    name: str = "planning"
    description: str = _PLANNING_TOOL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "description": "The command to execute. Available commands: create, update, list, get, set_active, mark_step, delete.",
                "enum": [
                    "create",
                    "update",
                    "list",
                    "get",
                    "set_active",
                    "mark_step",
                    "delete",
                ],
                "type": "string",
            },
            "plan_id": {
                "description": "Unique identifier for the plan. Required for create, update, set_active, and delete commands. Optional for get and mark_step (uses active plan if not specified).",
                "type": "string",
            },
            "title": {
                "description": "Title for the plan. Required for create command, optional for update command.",
                "type": "string",
            },
            "steps": {
                "description": "List of plan steps. Required for create command, optional for update command.",
                "type": "array",
                "items": {"type": "string"},
            },
            "step_index": {
                "description": "Index of the step to update (0-based). Required for mark_step command.",
                "type": "integer",
            },
            "step_status": {
                "description": "Status to set for a step. Used with mark_step command.",
                "enum": ["not_started", "in_progress", "completed", "blocked"],
                "type": "string",
            },
            "step_notes": {
                "description": "Additional notes for a step. Optional for mark_step command.",
                "type": "string",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    def __init__(self, agent: Optional[Any] = None, **kwargs):
        """Initialize the planning tool."""
        super().__init__(**kwargs)
        self.agent = agent
        self.plans = {}
        self.active_plan = None

    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Create a plan for a given task.
        
        Args:
            task: The task to create a plan for
            max_steps: Maximum number of steps (default: 5)
            
        Returns:
            Dictionary with the planning results
        """
        task = kwargs.get("task")
        max_steps = int(kwargs.get("max_steps", 5))
        
        if not task:
            return {
                "status": "error",
                "error": "No task provided"
            }
            
        try:
            if self.agent:
                # Use the agent to generate a plan
                plan = await self._generate_plan_with_agent(task, max_steps)
            else:
                # Create a basic plan without an agent
                plan = self._create_basic_plan(task, max_steps)
                
            return {
                "status": "success",
                "task": task,
                "plan": plan
            }
            
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            return {
                "status": "error",
                "error": f"Failed to create plan: {str(e)}"
            }

    async def execute(
        self,
        command: str,
        plan_id: Optional[str] = None,
        title: Optional[str] = None,
        steps: Optional[List[str]] = None,
        step_index: Optional[int] = None,
        step_status: Optional[str] = None,
        step_notes: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute a planning tool command."""
        try:
            if command == "create":
                if not title:
                    raise ValueError("Parameter `title` is required for command: create")
                return await self._create_plan(title=title, steps=steps)
            elif command == "update":
                return await self._update_plan(title=title, steps=steps, plan_id=plan_id)
            elif command == "list":
                return await self._list_plans()
            elif command == "get":
                return await self._get_plan(plan_id=plan_id)
            elif command == "set_active":
                return await self._set_active_plan(plan_id=plan_id)
            elif command == "mark_step":
                if step_index is None:
                    raise ValueError("Parameter `step_index` is required for command: mark_step")
                if step_status is None:
                    raise ValueError("Parameter `step_status` is required for command: mark_step")
                return await self._mark_step(
                    step_index=step_index,
                    step_status=step_status,
                    plan_id=plan_id,
                    step_notes=step_notes or ""
                )
            elif command == "delete":
                return await self._delete_plan(plan_id=plan_id)
            else:
                raise ValueError(f"Unknown command: {command}")
        except Exception as e:
            logger.error(f"Error executing planning tool command: {str(e)}")
            return {
                "status": "error",
                "error": f"Failed to execute command: {command}"
            }

    async def _generate_plan_with_agent(self, task: str, max_steps: int) -> List[Dict[str, str]]:
        """
        Generate a detailed plan using the agent.
        
        Args:
            task: The task to plan for
            max_steps: Maximum number of steps
            
        Returns:
            List of plan steps
        """
        prompt = f"""
        Create a plan for the following task: {task}
        
        The plan should:
        1. Break down the task into at most {max_steps} logical steps
        2. Be specific and actionable
        3. Include necessary resources or prerequisites
        
        Format the response as a JSON array of steps:
        [
            {{"step": 1, "description": "First step description", "tools": ["tool1", "tool2"]}},
            {{"step": 2, "description": "Second step description", "tools": ["tool3"]}}
        ]
        """
        
        if not self.agent:
            raise ValueError("Agent not available for planning")
            
        # Use the agent to generate the plan
        result = await self.agent.generate_content(prompt)
        
        # Extract JSON from the result
        try:
            # Find JSON content in the response
            response_text = result.get("response", "")
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                plan = json.loads(json_str)
                
                # Validate plan format
                if not isinstance(plan, list):
                    raise ValueError("Plan is not a list")
                    
                # Clean up and validate each step
                cleaned_plan = []
                for i, step in enumerate(plan):
                    if not isinstance(step, dict):
                        continue
                        
                    cleaned_step = {
                        "step": i + 1,
                        "description": step.get("description", ""),
                        "tools": step.get("tools", [])
                    }
                    cleaned_plan.append(cleaned_step)
                    
                return cleaned_plan
            else:
                raise ValueError("Could not find JSON array in response")
                
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON plan from agent response")
            # Fall back to basic plan
            return self._create_basic_plan(task, max_steps)
            
    def _create_basic_plan(self, task: str, max_steps: int) -> List[Dict[str, str]]:
        """
        Create a basic plan without using the agent.
        
        Args:
            task: The task to plan for
            max_steps: Maximum number of steps
            
        Returns:
            List of plan steps
        """
        # For a simple plan, just break the task into generic steps
        steps = [
            {
                "step": 1,
                "description": f"Analyze the requirements for: {task}",
                "tools": ["web_search"]
            },
            {
                "step": 2, 
                "description": "Gather necessary information and resources",
                "tools": ["web_search", "file_tool"]
            },
            {
                "step": 3,
                "description": "Implement the core solution",
                "tools": ["python_tool", "shell_tool"]
            }
        ]
        
        if max_steps > 3:
            steps.append({
                "step": 4,
                "description": "Test and verify the solution",
                "tools": ["python_tool", "shell_tool"]
            })
            
        if max_steps > 4:
            steps.append({
                "step": 5,
                "description": "Finalize and present the results",
                "tools": ["file_tool"]
            })
            
        return steps[:max_steps]

    async def _create_plan(self, title: str, steps: list = None, plan_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create a new plan."""
        if not plan_id:
            plan_id = f"plan_{int(asyncio.get_event_loop().time())}"
            
        if plan_id in self.plans:
            raise ValueError(f"A plan with ID '{plan_id}' already exists. Use 'update' to modify existing plans.")
            
        plan = {
            "title": title,
            "steps": steps or [],
            "step_statuses": ["not_started"] * len(steps or []),
            "step_notes": [""] * len(steps or []),
            "created_at": asyncio.get_event_loop().time()
        }
        
        self.plans[plan_id] = plan
        self.active_plan = plan_id
        
        return {
            "status": "success",
            "plan_id": plan_id,
            "plan": plan
        }

    async def _update_plan(self, title: str = None, steps: list = None, plan_id: str = None, **kwargs) -> Dict[str, Any]:
        """Update an existing plan."""
        if not plan_id:
            if not self.active_plan:
                raise ValueError("No active plan. Please specify a plan_id or set an active plan.")
            plan_id = self.active_plan
            
        if plan_id not in self.plans:
            raise ValueError(f"No plan found with ID: {plan_id}")
            
        plan = self.plans[plan_id]
        if title:
            plan["title"] = title
        if steps:
            plan["steps"] = steps
            plan["step_statuses"] = ["not_started"] * len(steps)
            plan["step_notes"] = [""] * len(steps)
            
        return {
            "status": "success",
            "plan_id": plan_id,
            "plan": plan
        }

    def _list_plans(self) -> Dict[str, Any]:
        """List all available plans."""
        if not self.plans:
            return {
                "status": "success",
                "message": "No plans available. Create a plan with the 'create' command."
            }

        output = "Available plans:\n"
        for plan_id, plan in self.plans.items():
            current_marker = " (active)" if plan_id == self.active_plan else ""
            completed = sum(
                1 for status in plan["step_statuses"] if status == "completed"
            )
            total = len(plan["steps"])
            progress = f"{completed}/{total} steps completed"
            output += f"• {plan_id}{current_marker}: {plan['title']} - {progress}\n"

        return {
            "status": "success",
            "message": output
        }

    def _get_plan(self, plan_id: Optional[str]) -> Dict[str, Any]:
        """Get details of a specific plan."""
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self.active_plan:
                raise ValueError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self.active_plan

        if plan_id not in self.plans:
            raise ValueError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]
        return {
            "status": "success",
            "plan_id": plan_id,
            "plan": plan
        }

    def _set_active_plan(self, plan_id: Optional[str]) -> Dict[str, Any]:
        """Set a plan as the active plan."""
        if not plan_id:
            raise ValueError("Parameter `plan_id` is required for command: set_active")

        if plan_id not in self.plans:
            raise ValueError(f"No plan found with ID: {plan_id}")

        self.active_plan = plan_id
        return {
            "status": "success",
            "plan_id": plan_id,
            "plan": self.plans[plan_id]
        }

    async def _mark_step(self, step_index: int, step_status: str, plan_id: str = None, step_notes: str = "", **kwargs) -> Dict[str, Any]:
        """Mark a step in a plan with a specific status."""
        if not plan_id:
            if not self.active_plan:
                raise ValueError("No active plan. Please specify a plan_id or set an active plan.")
            plan_id = self.active_plan
            
        if plan_id not in self.plans:
            raise ValueError(f"No plan found with ID: {plan_id}")
            
        plan = self.plans[plan_id]
        if step_index < 0 or step_index >= len(plan["steps"]):
            raise ValueError(f"Invalid step index: {step_index}")
            
        plan["step_statuses"][step_index] = step_status
        plan["step_notes"][step_index] = step_notes
        
        return {
            "status": "success",
            "plan_id": plan_id,
            "plan": plan
        }

    def _delete_plan(self, plan_id: Optional[str]) -> Dict[str, Any]:
        """Delete a plan."""
        if not plan_id:
            raise ValueError("Parameter `plan_id` is required for command: delete")

        if plan_id not in self.plans:
            raise ValueError(f"No plan found with ID: {plan_id}")

        del self.plans[plan_id]

        # If the deleted plan was the active plan, clear the active plan
        if self.active_plan == plan_id:
            self.active_plan = None

        return {
            "status": "success",
            "plan_id": plan_id,
            "message": f"Plan '{plan_id}' has been deleted."
        }

    def _format_plan(self, plan: Dict) -> str:
        """Format a plan for display."""
        # Find the plan_id by looking through self.plans
        plan_id = next((pid for pid, p in self.plans.items() if p == plan), "unknown")
        
        output = f"Plan: {plan['title']} (ID: {plan_id})\n"
        output += "=" * len(output) + "\n\n"

        # Calculate progress statistics
        total_steps = len(plan["steps"])
        completed = sum(1 for status in plan["step_statuses"] if status == "completed")
        in_progress = sum(
            1 for status in plan["step_statuses"] if status == "in_progress"
        )
        blocked = sum(1 for status in plan["step_statuses"] if status == "blocked")
        not_started = sum(
            1 for status in plan["step_statuses"] if status == "not_started"
        )

        output += f"Progress: {completed}/{total_steps} steps completed "
        if total_steps > 0:
            percentage = (completed / total_steps) * 100
            output += f"({percentage:.1f}%)\n"
        else:
            output += "(0%)\n"

        output += f"Status: {completed} completed, {in_progress} in progress, {blocked} blocked, {not_started} not started\n\n"
        output += "Steps:\n"

        # Add each step with its status and notes
        for i, (step, status, notes) in enumerate(
            zip(plan["steps"], plan["step_statuses"], plan["step_notes"])
        ):
            status_symbol = {
                "not_started": "[ ]",
                "in_progress": "[→]",
                "completed": "[✓]",
                "blocked": "[!]",
            }.get(status, "[ ]")

            output += f"{i}. {status_symbol} {step}\n"
            if notes:
                output += f"   • Note: {notes}\n"

        # Try to use PlanFormatter if available
        try:
            from app.display import PlanFormatter
            PlanFormatter.format_plan(output)
            # Since we're displaying the plan with PlanFormatter, return empty string
            # to avoid double display
            return ""
        except (ImportError, AttributeError):
            # If PlanFormatter is not available, just return the formatted string
            return output
