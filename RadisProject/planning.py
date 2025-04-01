async def run(self, **kwargs) -> Dict[str, Any]:
    """
    Handle both direct task input and command-based execution.

    Args:
        task: The task to create a plan for (for task-based calls)
        command: The command to execute (for command-based calls)
        max_steps: Maximum number of steps (default: 5)

    Returns:
        Dictionary with the planning results
    """
    try:
        # Validate input parameters
        params = self.validate_parameters(kwargs)

        # Check if this is a command-based call
        if params["command"] == "create":
            task = params["task"]
            max_steps = int(params.get("max_steps", 5))

            if self.agent:
                # Use the agent to generate a plan
                plan = await self._generate_plan_with_agent(task, max_steps)
            else:
                # Create a basic plan without an agent
                plan = self._create_basic_plan(task, max_steps)

            return {"status": "success", "task": task, "plan": plan}
        else:
            # Handle other commands through execute
            return await self.execute(**params)

    except jsonschema.ValidationError as e:
        return {"status": "error", "error": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.error(f"Error executing plan command: {e}")
        return {"status": "error", "error": f"Failed to execute command: {str(e)}"}
