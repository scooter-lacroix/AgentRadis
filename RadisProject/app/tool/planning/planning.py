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
            
            Format the response as a JSON array of steps where each step is a clear, actionable instruction.
            """
            
            # Send the prompt to the agent and get the response
            response = await self.agent.generate(prompt)
            
            if not response:
                if self.verbose:
                    display("Agent returned empty response. Falling back to basic plan.", "warning")
                return await self._generate_basic_plan(task)
            
            # Try to extract steps from the response
            steps = []
            
            # First, try to parse as JSON
            try:
                # Look for JSON array in the response
                json_match = re.search(r'\[\s*"[^"]*"(?:\s*,\s*"[^"]*")*\s*\]', response)
                if json_match:
                    json_str = json_match.group(0)
                    steps = json.loads(json_str)
                else:
                    # Try to parse the entire response as JSON
                    parsed_response = json.loads(response)
                    if isinstance(parsed_response, list):
                        steps = parsed_response
                    elif isinstance(parsed_response, dict) and "steps" in parsed_response:
                        steps = parsed_response["steps"]
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract steps using regex patterns
                lines = response.split('\n')
                
                # Look for numbered steps (e.g., "1. Do something")
                for line in lines:
                    step_match = re.match(r'^\s*(\d+)[.)\]]\s+(.+)$', line)
                    if step_match:
                        steps.append(step_match.group(2).strip())
            
            # If we couldn't extract steps, look for lines with "Step" in them
            if not steps:
                step_lines = [line for line in response.split('\n') if "step" in line.lower()]
                if step_lines:
                    steps = [line.strip() for line in step_lines]
            
            # If we still couldn't extract steps, split by newlines and filter out empty lines
            if not steps:
                steps = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Filter out any non-string items or empty strings
            steps = [step for step in steps if isinstance(step, str) and step.strip()]
            
            # If we couldn't extract any steps, fall back to basic plan
            if not steps:
                if self.verbose:
                    display("Could not extract steps from agent response. Falling back to basic plan.", "warning")
                return await self._generate_basic_plan(task)
            
            if self.verbose:
                display(f"Generated plan with {len(steps)} steps.", "info")
            
            return steps
            
        except Exception as e:
            if self.verbose:
                display(f"Error generating plan with agent: {str(e)}", "error")
                display(traceback.format_exc(), "error")
            
            # Fall back to basic plan on error
            return await self._generate_basic_plan(task)

    async def _generate_basic_plan(self, task: str) -> List[str]:
        """
        Generate a basic plan without using an AI agent.
        
        This method creates a simple, generic plan with standard steps for approaching a task.
        It's used as a fallback when an AI agent is not available or when agent-based 
        plan generation fails.
        
        Args:
            task: The task description to create a plan for
            
        Returns:
            List[str]: A list of basic plan steps
        """
        if self.verbose:
            display(f"Generating basic plan for task: {task}", "info")
        
        # Create a simple plan with generic steps
        steps = [
            f"Step 1: Understand the requirements for '{task}'",
            "Step 2: Break down the task into manageable components",
            "Step 3: Gather necessary resources and information",
            "Step 4: Implement a solution for each component",
            "Step 5: Test the implementation thoroughly",
            "Step 6: Review and refine the solution",
            "Step 7: Document the process and results",
            "Step 8: Finalize and deliver the completed task"
        ]
        
        return steps

    async def _save_plan(self, plan_id: str, plan: List[str]) -> None:
        """
        Save a plan to persistent storage.
        
        Args:
            plan_id: The unique identifier for the plan
            plan: The list of plan steps to save
            
        Raises:
            PlanningError: If the plan cannot be saved
        """
        try:
            plan_file = os.path.join(self.storage_dir, f"{plan_id}.json")
            
            plan_data = {
                "id": plan_id,
                "created_at": datetime.now().isoformat(),
                "steps": plan,
                "current_step": self.current_step_index,
                "failed_step": self.failed_step
            }
            
            with open(plan_file, 'w') as f:
                json.dump(plan_data, f, indent=2)
                
            if self.verbose:
                display(f"Plan saved to {plan_file}", "info")
                
        except Exception as e:
            error_message = f"Failed to save plan: {str(e)}"
            if self.verbose:
                display(error_message, "error")
            raise PlanningError(error_message)

    async def _load_plan(self, plan_id: str) -> List[str]:
        """
        Load a plan from persistent storage.
        
        Args:
            plan_id: The unique identifier of the plan to load
            
        Returns:
            List[str]: The loaded plan steps
            
        Raises:
            PlanningError: If the plan cannot be found or loaded
        """
        try:
            plan_file = os.path.join(self.storage_dir, f"{plan_id}.json")
            
            if not os.path.exists(plan_file):
                raise PlanningError(f"Plan with ID {plan_id} not found")
                
            with open(plan_file, 'r') as f:
                plan_data = json.load(f)
                
            # Extract the steps from the plan data
            steps = plan_data.get("steps", [])
            
            # Optionally restore other state information
            self.current_step_index = plan_data.get("current_step", 0)
            self.failed_step = plan_data.get("failed_step", None)
                
            if self.verbose:
                display(f"Plan loaded from {plan_file}", "info")
                
            return steps
            
        except json.JSONDecodeError:
            error_message = f"Failed to parse plan file for ID {plan_id}: invalid JSON"
            if self.verbose:
                display(error_message, "error")
            raise PlanningError(error_message)
            
        except Exception as e:
            error_message = f"Failed to load plan with ID {plan_id}: {str(e)}"
            if self.verbose:
                display(error_message, "error")
            raise PlanningError(error_message)

    async def _list_plans(self) -> List[Dict[str, Any]]:
        """
        List all available plans in the storage directory.
        
        Returns:
            List[Dict[str, Any]]: A list of plan metadata dictionaries
        """
        plans = []
        
        try:
            # Get all JSON files in the storage directory
            for filename in os.listdir(self.storage_dir):
                if filename.endswith(".json"):
                    try:
                        plan_id = filename.split(".")[0]
                        plan_file = os.path.join(self.storage_dir, filename)
                        
                        with open(plan_file, 'r') as f:
                            plan_data = json.load(f)
                            
                        # Extract relevant metadata
                        plan_info = {
                            "id": plan_id,
                            "created_at": plan_data.get("created_at", "Unknown"),
                            "step_count": len(plan_data.get("steps", [])),
                            "current_step": plan_data.get("current_step", 0)
                        }
                        
                        plans.append(plan_info)
                        
                    except Exception as e:
                        if self.verbose:
                            display(f"Error reading plan {filename}: {str(e)}", "warning")
                            
        except Exception as e:
            if self.verbose:
                display(f"Error listing plans: {str(e)}", "error")
                
        # Sort plans by creation date (newest first)
        plans.sort(key=lambda p: p.get("created_at", ""), reverse=True)
        
        return plans

    async def _delete_plan(self, plan_id: str) -> None:
        """
        Delete a plan from persistent storage.
        
        Args:
            plan_id: The unique identifier of the plan to delete
            
        Raises:
            PlanningError: If the plan cannot be found or deleted
        """
        try:
            plan_file = os.path.join(self.storage_dir, f"{plan_id}.json")
            
            if not os.path.exists(plan_file):
                raise PlanningError(f"Plan with ID {plan_id} not found")
                
            os.remove(plan_file)
            
            if self.verbose:
                display(f"Plan with ID {plan_id} deleted", "info")
                
        except Exception as e:
            if not isinstance(e, PlanningError):
                error_message = f"Failed to delete plan with ID {plan_id}: {str(e)}"
                if self.verbose:
                    display(error_message, "error")
                raise PlanningError(error_message)
            else:
                raise

    async def _validate_plan(self, plan: List[str]) -> Dict[str, Any]:
        """
        Validate a plan for completeness and coherence.
        
        Args:
            plan: The list of plan steps to validate
            
        Returns:
            Dict[str, Any]: Validation results with status and any issues found
        """
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        # Check if the plan has at least one step
        if not plan or len(plan) == 0:
            validation_result["valid"] = False
            validation_result["issues"].append("Plan has no steps")
            
        # Check if any step is empty
        for i, step in enumerate(plan):
            if not step.strip():
                validation_result["valid"] = False
                validation_result["issues"].append(f"Step {i+1} is empty")
                
        # Check for very short steps (potential lack of detail)
        for i, step in enumerate(plan):
            if len(step.strip()) < 10:  # Arbitrary threshold for a "short" step
                validation_result["warnings"].append(f"Step {i+1} is very short and may lack detail")
                
        # Warn if the plan has too few steps
        if len(plan) < 3:
            validation_result["warnings"].append("Plan has very few steps and may not be comprehensive")
            
        # Warn if the plan has too many steps
        if len(plan) > 20:
            validation_result["warnings"].append("Plan has many steps and may be overly complex")
            
        return validation_result

    async def _execute_plan(self, plan: List[str]) -> Dict[str, Any]:
        """
        Execute all steps in a plan sequentially.
        
        Args:
            plan: The list of plan steps to execute
            
        Returns:
            Dict[str, Any]: Execution results with status and details
        """
        if not plan:
            return {
                "status": "error",
                "message": "Cannot execute empty plan"
            }
            
        results = []
        success = True
        self.current_step_index = 0
        self.failed_step = None
        
        if self.verbose:
            display(f"Executing plan with {len(plan)} steps", "info")
            
        for i, step in enumerate(plan):
            if self.verbose:
                display(f"Executing step {i+1} of {len(plan)}: {step}", "info")
                
            step_result = await self._execute_step(step)
            results.append(step_result)
            
            # Check if the step failed
            if step_result.get("status") != "success":
                success = False
                self.failed_step = i
                if self.verbose:
                    display(f"Step {i+1} failed, aborting plan execution", "error")
                break
                
            self.current_step_index = i + 1
            
        # Save the current state of the plan
        if self.current_plan_id:
            await self._save_plan(self.current_plan_id, plan)
            
        return {
            "status": "success" if success else "error",
            "message": "Plan execution completed successfully" if success else f"Plan execution failed at step {self.failed_step + 1}",
            "results": results,
            "completed_steps": self.current_step_index,
            "total_steps": len(plan),
            "plan_id": self.current_plan_id,
            "failed_step": self.failed_step
        }

    async def _execute_step(self, step: str) -> Dict[str, Any]:
        """
        Execute a single step in a plan.
        
        This is a placeholder method that should be extended based on the specific
        capabilities of your application. In a real implementation, this might involve:
        - Parsing the step to identify required actions
        - Delegating to other tools or agents
        - Interacting with external systems
        - Gathering user input
        
        Args:
            step: The plan step to execute
            
        Returns:
            Dict[str, Any]: Execution results with status and details
        """
        # This is a placeholder implementation
        # In a real system, this would perform the actual execution logic
        
        try:
            if self.verbose:
                display(f"Executing step: {step}", "info")
                
            # Simulate execution time
            await asyncio.sleep(0.5)
            
            # For demonstration purposes, always succeed
            # In a real implementation, this would contain actual execution logic
            return {
                "status": "success",
                "message": f"Step executed: {step}",
                "details": {
                    "timestamp": datetime.now().isoformat(),
                    "duration": 0.5
                }
            }
            
        except Exception as e:
            if self.verbose:
                display(f"Error executing step: {str(e)}", "error")
                display(traceback.format_exc(), "error")
                
            return {
                "status": "error",
                "message": f"Failed to execute step: {str(e)}",
                "details": {
                    "error": str(e),
                    "trace": traceback.format_exc()
                }
            }

    async def cleanup(self) -> None:
        """
        Clean up any resources used by the tool.
        
        This method should be called when the tool is no longer needed.
        """
        # No resources to clean up in this implementation
        pass

    def reset(self) -> None:
        """
        Reset the tool state.
        
        This method resets the internal state of the tool, clearing any current plan
        and execution state.
        """
        self.current_plan = None
        self.current_plan_id = None
        self.current_step_index = 0
        self.current_step = None
        self.failed_step = None
        
        if self.verbose:
            display("Planning tool state reset", "info")
                    
