import json
import time
from typing import Dict, List, Optional, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, PlanStepStatus
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message, ToolChoice, AgentResult
from app.tool import PlanningTool
from app.exceptions import AgentRadisException


class PlanningFlow(BaseFlow):
    """A flow that manages planning and execution of tasks using agents."""

    llm: LLM = Field(default_factory=lambda: LLM())
    planning_tool: PlanningTool = Field(default_factory=PlanningTool)
    executor_keys: List[str] = Field(default_factory=list)
    active_plan_id: str = Field(default_factory=lambda: f"plan_{int(time.time())}")
    current_step_index: Optional[int] = None
    plan: Optional[dict] = None
    current_step: int = 0
    agent_results: List[str] = []

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # Set executor keys before super().__init__
        if "executors" in data:
            data["executor_keys"] = data.pop("executors")

        # Set plan ID if provided
        if "plan_id" in data:
            data["active_plan_id"] = data.pop("plan_id")

        # Initialize the planning tool if not provided
        if "planning_tool" not in data:
            planning_tool = PlanningTool()
            data["planning_tool"] = planning_tool

        # Call parent's init with the processed data
        super().__init__(agents, **data)

        # Set executor_keys to all agent keys if not specified
        if not self.executor_keys:
            self.executor_keys = list(self.agents.keys())

    def get_executor(self, step_type: Optional[str] = None) -> BaseAgent:
        """
        Get an appropriate executor agent for the current step.
        Can be extended to select agents based on step type/requirements.
        """
        # If step type is provided and matches an agent key, use that agent
        if step_type and step_type in self.agents:
            return self.agents[step_type]

        # Otherwise use the first available executor or fall back to primary agent
        for key in self.executor_keys:
            if key in self.agents:
                return self.agents[key]

        # Fallback to primary agent
        return self.primary_agent

    async def execute(self, prompt: str) -> str:
        """Execute the flow with the given prompt"""
        try:
            # Create initial plan
            self.plan = await self._create_plan(prompt)
            logger.info(f"Plan creation result: {self.plan}")

            # Execute each step
            total_steps = len(self.plan['steps'])
            for i, step in enumerate(self.plan['steps']):
                if self.plan['step_statuses'][i] != 'completed':
                    # Update progress
                    self.current_step = i

                    # Execute step with primary agent
                    agent = self.agents["radis"]
                    try:
                        result = await agent.run(step)
                        if isinstance(result, AgentResult):
                            self.agent_results.append(result)
                            if result.success:
                                self.plan['step_statuses'][i] = 'completed'
                            else:
                                self.plan['step_statuses'][i] = 'blocked'
                                self.plan['step_notes'][i] = result.error
                        else:
                            # Handle string results
                            self.plan['step_statuses'][i] = 'completed'
                            self.agent_results.append(str(result))

                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error executing step {i}: {error_msg}")
                        self.plan['step_statuses'][i] = 'blocked'
                        self.plan['step_notes'][i] = error_msg
                        if "ChatCompletionMessageToolCall" in error_msg:
                            raise AgentRadisException(
                                "Tool call format error. Please check API compatibility."
                            )
                        raise

            # Generate final response
            completed_steps = len([s for s in self.plan['step_statuses'] if s == 'completed'])
            if completed_steps == 0:
                return "Failed to complete any steps in the plan."

            # Generate a summary of the plan execution
            return await self._generate_final_summary()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in PlanningFlow: {error_msg}")
            if "ChatCompletionMessageToolCall" in error_msg:
                return "Error: The LLM's response format is incompatible with the tool call format. Please check API compatibility."
            return f"Execution failed: {error_msg}"

    async def _create_plan(self, request: str) -> dict:
        """Create an initial plan based on the request using the flow's LLM and PlanningTool."""
        logger.info(f"Creating initial plan with ID: {self.active_plan_id}")

        # Create a system message for plan creation
        system_message = Message(
            role="system",
            content="You are a planning assistant. Create a concise, actionable plan with clear steps. "
            "Focus on key milestones rather than detailed sub-steps. "
            "Optimize for clarity and efficiency."
        )

        # Create a user message with the request
        user_message = Message(
            role="user",
            content=f"Create a reasonable plan with clear steps to accomplish the task: {request}"
        )

        # Call LLM with PlanningTool
        response = await self.llm.ask_tool(
            messages=[user_message],
            system_msgs=[system_message],
            tools=[self.planning_tool.to_param()],
            tool_choice=ToolChoice.REQUIRED,
        )

        # Process tool calls if present
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "planning":
                    # Parse the arguments
                    args = tool_call.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse tool arguments: {args}")
                            continue

                    # Ensure plan_id is set correctly and execute the tool
                    args["plan_id"] = self.active_plan_id

                    # Execute the tool via ToolCollection instead of directly
                    result = await self.planning_tool.execute(**args)
                    logger.info(f"Plan creation result: {str(result)}")
                    
                    # Return the plan from the planning tool's storage
                    return self.planning_tool.plans[self.active_plan_id]

        # If execution reached here, create a default plan
        logger.warning("Creating default plan")

        # Create default plan using the ToolCollection
        await self.planning_tool.execute(
            **{
                "command": "create",
                "plan_id": self.active_plan_id,
                "title": f"Plan for: {request[:50]}{'...' if len(request) > 50 else ''}",
                "steps": ["Analyze request", "Execute task", "Verify results"],
            }
        )
        
        # Return the default plan from storage
        return self.planning_tool.plans[self.active_plan_id]

    async def _get_current_step_info(self) -> tuple[Optional[int], Optional[dict]]:
        """
        Parse the current plan to identify the first non-completed step's index and info.
        Returns (None, None) if no active step is found.
        """
        if (
            not self.active_plan_id
            or self.active_plan_id not in self.planning_tool.plans
        ):
            logger.error(f"Plan with ID {self.active_plan_id} not found")
            return None, None

        try:
            # Direct access to plan data from planning tool storage
            plan_data = self.planning_tool.plans[self.active_plan_id]
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])

            # Find first non-completed step
            for i, step in enumerate(steps):
                if i >= len(step_statuses):
                    status = PlanStepStatus.NOT_STARTED.value
                else:
                    status = step_statuses[i]

                if status in PlanStepStatus.get_active_statuses():
                    # Extract step type/category if available
                    step_info = {"text": step}

                    # Try to extract step type from the text (e.g., [SEARCH] or [CODE])
                    import re

                    type_match = re.search(r"\[([A-Z_]+)\]", step)
                    if type_match:
                        step_info["type"] = type_match.group(1).lower()

                    # Mark current step as in_progress
                    try:
                        await self.planning_tool.execute(
                            command="mark_step",
                            plan_id=self.active_plan_id,
                            step_index=i,
                            step_status=PlanStepStatus.IN_PROGRESS.value,
                        )
                    except Exception as e:
                        logger.warning(f"Error marking step as in_progress: {e}")
                        # Update step status directly if needed
                        if i < len(step_statuses):
                            step_statuses[i] = PlanStepStatus.IN_PROGRESS.value
                        else:
                            while len(step_statuses) < i:
                                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
                            step_statuses.append(PlanStepStatus.IN_PROGRESS.value)

                        plan_data["step_statuses"] = step_statuses

                    return i, step_info

            return None, None  # No active step found

        except Exception as e:
            logger.warning(f"Error finding current step index: {e}")
            return None, None

    async def _execute_step(self, executor: BaseAgent, step_info: dict) -> str:
        """Execute the current step with the specified agent using agent.run()."""
        # Prepare context for the agent with current plan status
        plan_status = await self._get_plan_text()
        step_text = step_info.get("text", f"Step {self.current_step_index}")

        # Create a prompt for the agent to execute the current step
        step_prompt = f"""
        CURRENT PLAN STATUS:
        {plan_status}

        YOUR CURRENT TASK:
        You are now working on step {self.current_step_index}: "{step_text}"

        Please execute this step using the appropriate tools. When you're done, provide a summary of what you accomplished.
        """

        # Use agent.run() to execute the step
        try:
            step_result = await executor.run(step_prompt)

            # Mark the step as completed after successful execution
            await self._mark_step_completed()

            return step_result
        except Exception as e:
            logger.error(f"Error executing step {self.current_step_index}: {e}")
            return f"Error executing step {self.current_step_index}: {str(e)}"

    async def _mark_step_completed(self) -> None:
        """Mark the current step as completed."""
        if self.current_step_index is None:
            return

        try:
            # Mark the step as completed
            await self.planning_tool.execute(
                command="mark_step",
                plan_id=self.active_plan_id,
                step_index=self.current_step_index,
                step_status=PlanStepStatus.COMPLETED.value,
            )
            logger.info(
                f"Marked step {self.current_step_index} as completed in plan {self.active_plan_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to update plan status: {e}")
            # Update step status directly in planning tool storage
            if self.active_plan_id in self.planning_tool.plans:
                plan_data = self.planning_tool.plans[self.active_plan_id]
                step_statuses = plan_data.get("step_statuses", [])

                # Ensure the step_statuses list is long enough
                while len(step_statuses) <= self.current_step_index:
                    step_statuses.append(PlanStepStatus.NOT_STARTED.value)

                # Update the status
                step_statuses[self.current_step_index] = PlanStepStatus.COMPLETED.value
                plan_data["step_statuses"] = step_statuses

    async def _get_plan_text(self) -> str:
        """Get the current plan as formatted text."""
        try:
            result = await self.planning_tool.execute(
                command="get", plan_id=self.active_plan_id
            )
            return result.output if hasattr(result, "output") else str(result)
        except Exception as e:
            logger.error(f"Error getting plan: {e}")
            return self._generate_plan_text_from_storage()

    def _generate_plan_text_from_storage(self) -> str:
        """Generate plan text directly from storage if the planning tool fails."""
        try:
            if self.active_plan_id not in self.planning_tool.plans:
                return f"Error: Plan with ID {self.active_plan_id} not found"

            plan_data = self.planning_tool.plans[self.active_plan_id]
            title = plan_data.get("title", "Untitled Plan")
            steps = plan_data.get("steps", [])
            step_statuses = plan_data.get("step_statuses", [])
            step_notes = plan_data.get("step_notes", [])

            # Ensure step_statuses and step_notes match the number of steps
            while len(step_statuses) < len(steps):
                step_statuses.append(PlanStepStatus.NOT_STARTED.value)
            while len(step_notes) < len(steps):
                step_notes.append("")

            # Count steps by status
            status_counts = {status: 0 for status in PlanStepStatus.get_all_statuses()}

            for status in step_statuses:
                if status in status_counts:
                    status_counts[status] += 1

            completed = status_counts[PlanStepStatus.COMPLETED.value]
            total = len(steps)
            progress = (completed / total) * 100 if total > 0 else 0

            plan_text = f"Plan: {title} (ID: {self.active_plan_id})\n"
            plan_text += "=" * len(plan_text) + "\n\n"

            plan_text += (
                f"Progress: {completed}/{total} steps completed ({progress:.1f}%)\n"
            )
            plan_text += f"Status: {status_counts[PlanStepStatus.COMPLETED.value]} completed, {status_counts[PlanStepStatus.IN_PROGRESS.value]} in progress, "
            plan_text += f"{status_counts[PlanStepStatus.BLOCKED.value]} blocked, {status_counts[PlanStepStatus.NOT_STARTED.value]} not started\n\n"
            plan_text += "Steps:\n"

            status_marks = PlanStepStatus.get_status_marks()

            for i, (step, status, notes) in enumerate(
                zip(steps, step_statuses, step_notes)
            ):
                # Use status marks to indicate step status
                status_mark = status_marks.get(
                    status, status_marks[PlanStepStatus.NOT_STARTED.value]
                )

                plan_text += f"{i}. {status_mark} {step}\n"
                if notes:
                    plan_text += f"   Notes: {notes}\n"

            return plan_text
        except Exception as e:
            logger.error(f"Error generating plan text from storage: {e}")
            return f"Error: Unable to retrieve plan with ID {self.active_plan_id}"

    async def _finalize_plan(self) -> str:
        """Finalize the plan and provide a summary using the flow's LLM directly."""
        plan_text = await self._get_plan_text()

        # Create a summary using the flow's LLM directly
        try:
            system_message = Message.system_message(
                "You are a planning assistant. Your task is to summarize the completed plan."
            )

            user_message = Message.user_message(
                f"The plan has been completed. Here is the final plan status:\n\n{plan_text}\n\nPlease provide a summary of what was accomplished and any final thoughts."
            )

            response = await self.llm.ask(
                messages=[user_message], system_msgs=[system_message]
            )

            return f"Plan completed:\n\n{response}"
        except Exception as e:
            logger.error(f"Error finalizing plan with LLM: {e}")

            # Fallback to using an agent for the summary
            try:
                agent = self.primary_agent
                summary_prompt = f"""
                The plan has been completed. Here is the final plan status:

                {plan_text}

                Please provide a summary of what was accomplished and any final thoughts.
                """
                summary = await agent.run(summary_prompt)
                return f"Plan completed:\n\n{summary}"
            except Exception as e2:
                logger.error(f"Error finalizing plan with agent: {e2}")
                return "Plan completed. Error generating summary."

    async def _generate_final_summary(self) -> str:
        """Generate a comprehensive summary of the execution results.
        
        This creates a user-friendly summary of the plan execution, including
        step completion status and results from each step.
        
        Returns:
            A formatted string containing the final response with plan summary
        """
        try:
            # Get the plan's title and overall statistics
            plan_title = self.plan.get('title', 'Executed Plan')
            total_steps = len(self.plan['steps'])
            completed_steps = len([s for s in self.plan['step_statuses'] if s == 'completed'])
            completion_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
            
            # Start building the summary
            summary = []
            summary.append(f"Plan: {plan_title}")
            summary.append(f"Completion: {completed_steps}/{total_steps} steps ({completion_percentage:.1f}%)")
            summary.append("")
            
            # Add individual step results
            for i, (step, status) in enumerate(zip(self.plan['steps'], self.plan['step_statuses'])):
                step_num = i + 1
                status_symbol = "✓" if status == 'completed' else "✗"
                summary.append(f"Step {step_num}: {status_symbol} {step}")
                
                # Add the result for this step if available
                if i < len(self.agent_results):
                    result = self.agent_results[i]
                    if isinstance(result, AgentResult):
                        summary.append(f"{result.response}")
                    else:
                        summary.append(f"{result}")
                    summary.append("")
            
            # Try to generate a better summary if LLM is available
            try:
                enhanced_summary = await self._get_llm_enhanced_summary(summary)
                if enhanced_summary:
                    return enhanced_summary
            except Exception as e:
                logger.warning(f"Could not generate enhanced summary: {e}")
            
            # Fall back to basic summary if LLM enhancement fails
            return "\n".join(summary)
        except Exception as e:
            logger.error(f"Error generating final summary: {e}")
            # Fallback to basic response
            response = []
            for i, result in enumerate(self.agent_results):
                if isinstance(result, AgentResult):
                    response.append(f"Step {i+1}: {result.response}")
                else:
                    response.append(f"Step {i+1}: {result}")
            return "\n".join(response)

    async def _get_llm_enhanced_summary(self, summary_lines: List[str]) -> Optional[str]:
        """Use the LLM to generate an enhanced, natural language summary of the execution.
        
        Args:
            summary_lines: List of summary lines to enhance
            
        Returns:
            Enhanced summary or None if enhancement failed
        """
        basic_summary = "\n".join(summary_lines)
        
        system_message = Message.system_message(
            "You are a helpful assistant that summarizes plan execution results. "
            "Create a natural, concise summary that clearly explains what was accomplished, "
            "highlighting key findings or results. Be direct and focus on the most important information."
        )
        
        user_message = Message.user_message(
            f"Below is the execution result of a plan. Please summarize it in a clear, concise way "
            f"that highlights what was accomplished and any important findings:\n\n{basic_summary}"
        )
        
        try:
            response = await self.llm.ask(
                messages=[user_message], 
                system_msgs=[system_message]
            )
            
            if response and len(response) > 10:  # Ensure we got a meaningful response
                return response
            return None
        except Exception as e:
            logger.warning(f"Error generating enhanced summary: {e}")
            return None
