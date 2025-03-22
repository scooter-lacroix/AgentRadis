# tool/planning.py
from typing import Dict, List, Literal, Optional
import time

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult


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

    def __init__(self):
        self.plans = {}
        self.active_plan = None

    async def run(self, command: str, **kwargs) -> str:
        """Execute the planning tool command."""
        try:
            # Remove plan_id from kwargs if it's None
            if "plan_id" in kwargs and kwargs["plan_id"] is None:
                del kwargs["plan_id"]
                
            result = await self.execute(command=command, **kwargs)
            return result.output
        except Exception as e:
            raise Exception(f"Error executing planning tool command: {str(e)}")

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
    ) -> ToolResult:
        """Execute a planning tool command."""
        try:
            if command == "create":
                if not title:
                    raise ToolError("Parameter `title` is required for command: create")
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
                    raise ToolError("Parameter `step_index` is required for command: mark_step")
                if step_status is None:
                    raise ToolError("Parameter `step_status` is required for command: mark_step")
                return await self._mark_step(
                    step_index=step_index,
                    step_status=step_status,
                    plan_id=plan_id,
                    step_notes=step_notes or ""
                )
            elif command == "delete":
                return await self._delete_plan(plan_id=plan_id)
            else:
                raise ToolError(f"Unknown command: {command}")
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(f"Error executing planning tool command: {str(e)}")

    async def _create_plan(self, title: str, steps: list = None, plan_id: str = None, **kwargs) -> ToolResult:
        """Create a new plan."""
        if not plan_id:
            plan_id = f"plan_{int(time.time())}"
            
        if plan_id in self.plans:
            raise ToolError(f"A plan with ID '{plan_id}' already exists. Use 'update' to modify existing plans.")
            
        plan = {
            "title": title,
            "steps": steps or [],
            "step_statuses": ["not_started"] * len(steps or []),
            "step_notes": [""] * len(steps or []),
            "created_at": time.time()
        }
        
        self.plans[plan_id] = plan
        self.active_plan = plan_id
        
        return ToolResult(
            output=f"Created plan '{plan_id}':\n\n{self._format_plan(plan)}"
        )

    async def _update_plan(self, title: str = None, steps: list = None, plan_id: str = None, **kwargs) -> ToolResult:
        """Update an existing plan."""
        if not plan_id:
            if not self.active_plan:
                raise ToolError("No active plan. Please specify a plan_id or set an active plan.")
            plan_id = self.active_plan
            
        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")
            
        plan = self.plans[plan_id]
        if title:
            plan["title"] = title
        if steps:
            plan["steps"] = steps
            plan["step_statuses"] = ["not_started"] * len(steps)
            plan["step_notes"] = [""] * len(steps)
            
        return ToolResult(
            output=f"Updated plan '{plan_id}':\n\n{self._format_plan(plan)}"
        )

    def _list_plans(self) -> ToolResult:
        """List all available plans."""
        if not self.plans:
            return ToolResult(
                output="No plans available. Create a plan with the 'create' command."
            )

        output = "Available plans:\n"
        for plan_id, plan in self.plans.items():
            current_marker = " (active)" if plan_id == self.active_plan else ""
            completed = sum(
                1 for status in plan["step_statuses"] if status == "completed"
            )
            total = len(plan["steps"])
            progress = f"{completed}/{total} steps completed"
            output += f"• {plan_id}{current_marker}: {plan['title']} - {progress}\n"

        return ToolResult(output=output)

    def _get_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Get details of a specific plan."""
        if not plan_id:
            # If no plan_id is provided, use the current active plan
            if not self.active_plan:
                raise ToolError(
                    "No active plan. Please specify a plan_id or set an active plan."
                )
            plan_id = self.active_plan

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        plan = self.plans[plan_id]
        return ToolResult(output=self._format_plan(plan))

    def _set_active_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Set a plan as the active plan."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: set_active")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        self.active_plan = plan_id
        return ToolResult(
            output=f"Plan '{plan_id}' is now the active plan.\n\n{self._format_plan(self.plans[plan_id])}"
        )

    async def _mark_step(self, step_index: int, step_status: str, plan_id: str = None, step_notes: str = "", **kwargs) -> ToolResult:
        """Mark a step in a plan with a specific status."""
        if not plan_id:
            if not self.active_plan:
                raise ToolError("No active plan. Please specify a plan_id or set an active plan.")
            plan_id = self.active_plan
            
        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")
            
        plan = self.plans[plan_id]
        if step_index < 0 or step_index >= len(plan["steps"]):
            raise ToolError(f"Invalid step index: {step_index}")
            
        plan["step_statuses"][step_index] = step_status
        plan["step_notes"][step_index] = step_notes
        
        return ToolResult(
            output=f"Updated step {step_index} in plan '{plan_id}':\n\n{self._format_plan(plan)}"
        )

    def _delete_plan(self, plan_id: Optional[str]) -> ToolResult:
        """Delete a plan."""
        if not plan_id:
            raise ToolError("Parameter `plan_id` is required for command: delete")

        if plan_id not in self.plans:
            raise ToolError(f"No plan found with ID: {plan_id}")

        del self.plans[plan_id]

        # If the deleted plan was the active plan, clear the active plan
        if self.active_plan == plan_id:
            self.active_plan = None

        return ToolResult(output=f"Plan '{plan_id}' has been deleted.")

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
