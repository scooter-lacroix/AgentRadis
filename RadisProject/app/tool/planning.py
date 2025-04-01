"""
Planning Tool Module

This module provides a comprehensive planning tool that enables the creation,
validation, execution, and management of plans. The PlanningTool class serves as
the primary interface for plan generation and lifecycle management.
"""

import json
import re
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import asyncio
import os
import uuid

from app.tool.base import BaseTool
from app.errors import PlanningError

try:
    from app.display import display
except ImportError:
    # Fallback for display function if not available
    def display(message, level="info"):
        print(f"[{level.upper()}] {message}")


class PlanningTool(BaseTool):
    """
    A comprehensive tool for creating, validating, executing, and managing plans.
    
    The PlanningTool provides capabilities for generating step-by-step plans using
    AI agents, executing those plans, and managing plan lifecycle operations including
    validation, storage, retrieval, and cleanup.
    """
    
    @property
    def name(self) -> str:
        """Get the name of the tool."""
        return "planning"
    
    @property
    def description(self) -> str:
        """Get the description of the tool."""
        return "Create and execute step-by-step plans for completing complex tasks"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """Define the parameters schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Action to execute (create, validate, execute, save, load, list, delete)",
                    "enum": [
                        "create",
                        "validate",
                        "execute",
                        "execute_step",
                        "save",
                        "load",
                        "list",
                        "get_status",
                        "reset",
                        "delete"
                    ]
                },
                "task": {
                    "type": "string",
                    "description": "Task description for plan creation"
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of step descriptions for manual plan creation"
                },
                "plan_id": {
                    "type": "string",
                    "description": "ID of the plan to operate on"
                },
                "validate": {
                    "type": "boolean",
                    "description": "Whether to validate the generated plan"
                },
                "reset": {
                    "type": "boolean",
                    "description": "Whether to reset the current plan state"
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Whether to display verbose output"
                }
            },
            "required": []  # No required fields to support both approaches
        }
    
    def __init__(self, **kwargs):
        """
        Initialize the PlanningTool.
        
        Args:
            **kwargs: Additional keyword arguments to be passed to the parent class constructor.
        """
        super().__init__(**kwargs)
        self.agent = kwargs.get("agent", None)
        self.storage_dir = kwargs.get("storage_dir", os.path.join(os.getcwd(), "plans"))
        self.current_plan = None
        self.current_plan_id = None
        self.current_step_index = 0
        self.current_step = None
        self.failed_step = None
        self.verbose = kwargs.get("verbose", False)
        
        # Ensure storage directory exists
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

async def run(self, *args, **kwargs) -> Dict[str, Any]:
    """
    Run the planning tool with either positional or keyword arguments.
    
    This method serves as the main entry point for the PlanningTool and supports
    both positional arguments (direct task specification) and keyword arguments
    (command-based approach).
    
    Args:
        *args: If provided, the first arg is treated as the prompt
        **kwargs: Keyword arguments including 'prompt' or 'task'
            prompt: The task description for plan creation (alternative to task)
            task: The task description for plan creation (backward compatibility)
            command: The planning command to execute
            steps: List of steps for manual plan creation
            plan_id: ID of an existing plan to operate on
            validate: Whether to validate the generated plan
            reset: Whether to reset the current plan state
            verbose: Whether to display verbose output
    
    Returns:
        Dict[str, Any]: A dictionary containing the plan and status
    
    Raises:
        PlanningError: If an error occurs during planning operations.
    """
    prompt = None
    
    # Handle positional arguments
    if args and len(args) > 0:
        prompt = args[0]
    
    # Handle keyword arguments (with backward compatibility)
    if not prompt:
        prompt = kwargs.get('prompt')
    
    # For backward compatibility with 'task' parameter
    if not prompt:
        prompt = kwargs.get('task')
    
    if prompt:
        kwargs["task"] = prompt
    
    command = kwargs.get("command", "create" if kwargs.get("task") else None)
    self.verbose = kwargs.get("verbose", self.verbose)
    
    try:
        if command == "create" or kwargs.get("task"):
            # Create a new plan either from a task description or from provided steps
            task = kwargs.get("task")
            steps = kwargs.get("steps", None)
            
            if task and not steps:
                # Generate a plan based on the task description
                plan = await self._generate_plan_with_agent(task)
                self.current_plan = plan
                self.current_plan_id = str(uuid.uuid4())
                self.current_step_index = 0
                await self._save_plan(self.current_plan_id, plan)
                
                result = {
                    "status": "success",
                    "message": f"Plan created with ID: {self.current_plan_id}",
                    "plan_id": self.current_plan_id,
                    "plan": plan,
                    "task": task  # Include the task in the response
                }
                
                if kwargs.get("validate", False):
                    validation_result = await self._validate_plan(plan)
                    result["validation"] = validation_result
                
                return result
                
            elif steps:
                # Create a plan from provided steps
                plan = steps
                self.current_plan = plan
                self.current_plan_id = str(uuid.uuid4())
                self.current_step_index = 0
                await self._save_plan(self.current_plan_id, plan)
                
                return {
                    "status": "success",
                    "message": f"Plan created with ID: {self.current_plan_id}",
                    "plan_id": self.current_plan_id,
                    "plan": plan,
                    "task": task  # Include the task in the response
                }
            else:
                raise PlanningError("No task description or steps provided for plan creation")
    
        elif command == "load":
            # Load an existing plan
            plan_id = kwargs.get("plan_id")
            if not plan_id:
                raise PlanningError("No plan_id provided for loading")
            
            plan = await self._load_plan(

    async def _generate_plan_with_agent(self, task: str) -> List[str]:
        """
        Generate a plan using the AI agent.
        
        This method attempts to use an AI agent to create a detailed plan for
        accomplishing the given task. If an agent is not available or fails,
        it falls back to a basic plan.
        
        Args:
            task: The task description to create a plan for
            
        Returns:
            List[str]: A list of plan steps
        """
        if not self.agent:
            if self.verbose:
                display("No agent available. Falling back to basic plan.", "warning")
            return await self._generate_basic_plan(task)
        
        try:
            if self.verbose:
                display(f"Generating plan with agent for task: {task}", "info")
            
            # Create a prompt for the agent
            prompt = f"""
            Create a detailed step-by-step plan for the following task: {task}
            
            The plan should:
            1. Break down the task into logical, sequential steps
            2. Be specific and actionable 
            3. Include necessary tools or resources for each step
            4. Cover all aspects of the task from start to completion
            
            Format the response as a JSON array of steps where each step is a string:
            ["Step 1: Do this first", "Step 2: Then do this", "Step 3: Finally do this"]
            """
            
            # Call the agent to generate the plan
            result = await self.agent.generate_content(prompt)
            
            # Parse the result - this will vary based on your agent's response format
            if hasattr(result, 'content'):
                response_text = result.content
            elif isinstance(result, dict):
                response_text = result.get("response", "")
            else:
                response_text = str(result)
                
            # Extract JSON array from the response
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                try:
                    steps = json.loads(json_str)
                    if isinstance(steps, list) and len(steps) > 0:
                        if self.verbose:
                            display(f"Generated plan with {len(steps)} steps", "info")
                        return steps
                except json.JSONDecodeError:
                    if self.verbose:
                        display("Failed to parse JSON from agent response", "warning")
            
            # If we get here, extraction failed - try a regex approach as fallback
            import re
            steps = []
            step_pattern = r'\"(Step \d+:.*?)\"'
            matches = re.findall(step_pattern, response_text)
            
            if matches:
                steps = matches
                if self.verbose:
                    display(f"Extracted {len(steps)} steps using regex", "info")
                return steps
            
            # Last resort: try to extract any quoted strings
            quoted_strings = re.findall(r'\"(.*?)\"', response_text)
            if quoted_strings and len(quoted_strings) > 1:  # More than one is likely a list
                steps = quoted_strings
                if self.verbose:
                    display(f"Extracted {len(steps)} quoted strings as steps", "info")
                return steps
            
            # If all extraction methods fail, fall back to basic plan
            if self.verbose:
                display("Could not extract meaningful plan from agent. Using basic plan.", "warning")
            return await self._generate_basic_plan(task)
            
        except Exception as e:
            if self.verbose:
                display(f"Error generating plan with agent: {str(e)}", "error")
            return await self._generate_basic_plan(task)

    async def _generate_basic_plan(self, task: str) -> List[str]:
        """
        Generate a basic plan without using an agent.
        
        Args:
            task: The task description to create a plan for
            
        Returns:
            List[str]: A list of plan steps
        """
        if self.verbose:
            display("Generating basic plan (no agent available)", "info")
        
        # Create a simple 3-step plan
        return [
            f"Step 1: Analyze the requirements for: {task}",
            "Step 2: Implement the necessary components",
            "Step 3: Test and verify the implementation"
        ]

    async def _save_plan(self, plan_id: str, plan: List[str]) -> None:
        """
        Save a plan to storage.
        
        Args:
            plan_id: ID of the plan
            plan: List of plan steps
        """
        plan_path = os.path.join(self.storage_dir, f"{plan_id}.json")
        with open(plan_path, "w") as f:
            plan_data = {
                "id": plan_id,
                "created_at": datetime.now().isoformat(),
                "steps": plan
            }
            json.dump(plan_data, f, indent=2)
        
        if self.verbose:
            display(f"Plan saved to {plan_path}", "info")

    async def _load_plan(self, plan_id: str) -> List[str]:
        """
        Load a plan from storage.
        
        Args:
            plan_id: ID of the plan to load
            
        Returns:
            List[str]: The loaded plan steps
            
        Raises:
            PlanningError: If the plan doesn't exist
        """
        plan_path = os.path.join(self.storage_dir, f"{plan_id}.json")
        if not os.path.exists(plan_path):
            raise PlanningError(f"Plan not found: {plan_id}")
        
        with open(plan_path, "r") as f:
            try:
                plan_data = json.load(f)
                steps = plan_data.get("steps", [])
                
                if self.verbose:
                    display(f"Loaded plan {plan_id} with {len(steps)} steps", "info")
                
                return steps
            except json.JSONDecodeError:
                raise PlanningError(f"Invalid plan file: {plan_id}")

    async def _list_plans(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available plans.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of plans indexed by ID
        """
        plans = {}
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith(".json"):
                plan_id = filename[:-5]  # Remove .json extension
                plan_path = os.path.join(self.storage_dir, filename)
                
                try:
                    with open(plan_path, "r") as f:
                        plan_data = json.load(f)
                        plans[plan_id] = {
                            "id": plan_id,
                            "created_at": plan_data.get("created_at", "unknown"),
                            "step_count": len(plan_data.get("steps", [])),
                            "steps": plan_data.get("steps", [])
                        }
                except Exception as e:
                    if self.verbose:
                        display(f"Error loading plan {plan_id}: {str(e)}", "warning")
        
        return plans

    async def _delete_plan(self, plan_id: str) -> None:
        """
        Delete a plan from storage.
        
        Args:
            plan_id: ID of the plan to delete
            
        Raises:
            PlanningError: If the plan doesn't exist
        """
        plan_path = os.path.join(self.storage_dir, f"{plan_id}.json")
        if not os.path.exists(plan_path):
            raise PlanningError(f"Plan not found: {plan_id}")
        
        os.remove(plan_path)
        
        if self.verbose:
            display(f"Deleted plan {plan_id}", "info")

    async def _validate_plan(self, plan: List[str]) -> Dict[str, Any]:
        """
        Validate a plan.
        
        Args:
            plan: List of plan steps
            
        Returns:
            Dict[str, Any]: Validation results
        """
        if not plan:
            return {
                "valid": False,
                "issues": ["Plan is empty"]
            }
        
        issues = []
        
        # Check for empty steps
        for i, step in enumerate(plan):
            if not step.strip():
                issues.append(f"Step {i+1} is empty")
        
        # TODO: Add more validation rules as needed
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "step_count": len(plan)
        }

    async def _execute_plan(self, plan: List[str]) -> Dict[str, Any]:
        """
        Execute a plan step by step.
        
        Args:
            plan: List of plan steps
            
        Returns:
            Dict[str, Any]: Execution results
        """
        if self.verbose:
            display(f"Executing plan with {len(plan)} steps", "info")
        
        results = []
        success = True
        
        for i, step in enumerate(plan):
            if self.verbose:
                display(f"Executing step {i+1}/{len(plan)}: {step}", "info")
            
            try:
                step_result = await self._execute_step(step)
                results.append(step_result)
                
                if step_result.get("status") != "success":
                    success = False
                    self.failed_step = {
                        "index": i,
                        "step": step,
                        "result": step_result
                    }
                    break
                    
            except Exception as e:
                success = False
                error_message = str(e)
                
                if self.verbose:
                    display(f"Error executing step {i+1}: {error_message}", "error")
                
                self.failed_step = {
                    "index": i,
                    "step": step,
                    "error": error_message
                }
                
                results.append({
                    "status": "error",
                    "message": error_message
                })
                
                break
        
        return {
            "status": "success" if success else "error",
            "message": "Plan executed successfully" if success else f"Plan execution failed at step {len(results)}",
            "results": results,
            "completed_steps": len(results),
            "total_steps": len(plan)
        }

    async def _execute_step(self, step: str) -> Dict[str, Any]:
        """
        Execute a single plan step.
        
        Args:
            step: The step to execute
            
        Returns:
            Dict[str, Any]: Execution result
        """
        # This is a placeholder implementation
        # In a real implementation, this would perform the actual execution logic
        if self.verbose:
            display(f"Simulating execution of: {step}", "info")
        
        # Simulate a step execution
        await asyncio.sleep(0.5)
        
        return {
            "status": "success",
            "message": f"Executed: {step}"
        }

    async def cleanup(self) -> None:
        """Clean up any resources used by the tool."""
        # Reset the tool state
        self.current_plan = None
        self.current_plan_id = None
        self.current_step_index = 0
        self.current_step = None
        self.failed_step = None
        
        if self.verbose:
            display("Planning tool cleaned up", "info")

    async def reset(self) -> None:
        """Reset the tool to its initial state."""
        await self.cleanup()
        
        if self.verbose:
            display("Planning tool reset", "info")
