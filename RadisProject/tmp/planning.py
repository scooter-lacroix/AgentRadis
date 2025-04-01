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
                
                plan = await self._load_plan(plan_id)
                self.current_plan = plan
                self.current_plan_id = plan_id
                self.current_step_index = 0
                
                return {
                    "status": "success",
                    "message": f"Plan loaded with ID: {plan_id}",
                    "plan_id": plan_id,
                    "plan": plan
                }
            
            elif command == "execute":
                # Execute the current plan or a specified plan
                plan_id = kwargs.get("plan_id")
                if plan_id and plan_id != self.current_plan_id:
                    plan = await self._load_plan(plan_id)
                    self.current_plan = plan
                    self.current_plan_id = plan_id
                    self.current_step_index = 0
                
                if not self.current_plan:
                    raise PlanningError("No current plan to execute")
                
                return await self._execute_plan(self.current_plan)
            
            elif command == "execute_step":
                # Execute the next step in the current plan
                if not self.current_plan:
                    raise PlanningError("No current plan to execute step from")
                
                if self.current_step_index >= len(self.current_plan):
                    return {
                        "status": "complete", 
                        "message": "Plan execution completed",
                        "plan_id": self.current_plan_id
                    }
                
                step_result = await self._execute_step(self.current_plan[self.current_step_index])
                self.current_step_index += 1
                
                return {
                    "status": "success" if step_result["status"] == "success" else "error",
                    "message": f"Executed step {self.current_step_index} of {len(self.current_plan)}",
                    "step_index": self.current_step_index - 1,
                    "step_result": step_result,
                    "next_step_index": self.current_step_index if self.current_step_index < len(self.current_plan) else None,
                    "next_step": self.current_plan[self.current_step_index] if self.current_step_index < len(self.current_plan) else None,
                    "plan_id": self.current_plan_id
                }
            
            elif command == "validate":
                # Validate the current plan or a specified plan
                plan_id = kwargs.get("plan_id")
                if plan_id and plan_id != self.current_plan_id:
                    plan = await self._load_plan(plan_id)
                else:
                    plan = self.current_plan
                
                if not plan:
                    raise PlanningError("No plan to validate")
                
                validation_result = await self._validate_plan(plan)
                
                return {
                    "status": "success",
                    "message": "Plan validation completed",
                    "validation": validation_result,
                    "plan_id": self.current_plan_id
                }
            
            elif command == "list":
                # List all available plans
                plans = await self._list_plans()
                
                return {
                    "status": "success",
                    "message": f"Found {len(plans)} plans",
                    "plans": plans
                }
            
            elif command == "get_status":
                # Get the current status of plan execution
                if not self.current_plan:
                    return {
                        "status": "no_plan",
                        "message": "No current plan"
                    }
                
                return {
                    "status": "in_progress",
                    "message": f"Plan execution in progress: step {self.current_step_index} of {len(self.current_plan)}",
                    "plan_id": self.current_plan_id,
                    "current_step_index": self.current_step_index,
                    "total_steps": len(self.current_plan),
                    "current_step": self.current_plan[self.current_step_index] if self.current_step_index < len(self.current_plan) else None,
                    "failed_step": self.failed_step
                }
            
            elif command == "reset":
                # Reset the current plan execution state
                self.current_step_index = 0
                self.failed_step = None
                
                return {
                    "status": "success",
                    "message": "Plan execution state reset",
                    "plan_id": self.current_plan_id
                }
            
            elif command == "delete":
                # Delete a plan
                plan_id = kwargs.get("plan_id")
                if not plan_id:
                    raise PlanningError("No plan_id provided for deletion")
                
                await self._delete_plan(plan_id)
                
                if plan_id == self.current_plan_id:
                    self.current_plan = None
                    self.current_plan_id = None
                    self.current_step_index = 0
                    self.failed_step = None
                
                return {
                    "status": "success",
                    "message": f"Plan with ID {plan_id} deleted"
                }
            
            else:
                raise PlanningError(f"Unknown command: {command}")
        
        except Exception as e:
            error_message = str(e)
            stack_trace = traceback.format_exc()
            
            if isinstance(e, PlanningError):
                if self.verbose:
                    display(f"PlanningError: {error_message}", "error")
                return {
                    "status": "error",
                    "error_type": "PlanningError",
                    "message": error_message
                }
            else:
                if self.verbose:
                    display(f"Error during planning operation: {error_message}", "error")
                    display(stack_trace, "error")
                return {
                    "status": "error",
                    "error_type": type(e).__name__,
                    "message": error_message,
                    "stack_trace": stack_trace
                }

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
            
            Format the response as a JSON array of steps where each
"""

