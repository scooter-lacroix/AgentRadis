async def execute_tool(self, tool_call: ToolCall) -> ToolResponse:
    """
    Add compatibility with BaseAgent execute_tool method which takes a ToolCall object.
    This is important for parent class operations.

    Args:
        tool_call: The tool call to execute

    Returns:
        ToolResponse containing the result
    """
    tool_name = ""
    tool_args = {}

    # Extract tool name and arguments based on object type
    if isinstance(tool_call, dict):
        if "function" in tool_call:
            tool_name = tool_call["function"].get("name", "")
            args_str = tool_call["function"].get("arguments", "{}")
        else:
            tool_name = tool_call.get("name", "")
            args_str = tool_call.get("arguments", "{}")
    elif hasattr(tool_call, "function") and hasattr(tool_call.function, "name"):
        tool_name = tool_call.function.name
        args_str = tool_call.function.arguments
    elif hasattr(tool_call, "name"):
        tool_name = tool_call.name
        args_str = getattr(tool_call, "arguments", "{}")

    # Parse arguments
    if isinstance(args_str, str):
        try:
            tool_args = json.loads(args_str)
        except json.JSONDecodeError:
            tool_args = {"text": args_str}
    elif isinstance(args_str, dict):
        tool_args = args_str

    # Execute the tool with proper arguments
    try:
        result = await self._execute_tool(tool_name, tool_args)
        return ToolResponse(
            call_id=getattr(tool_call, "id", str(uuid.uuid4())),
            tool_name=tool_name,
            success=True,
            result=result,
            error=None,
        )
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        return ToolResponse(
            call_id=getattr(tool_call, "id", str(uuid.uuid4())),
            tool_name=tool_name,
            success=False,
            result=None,
            error=str(e),
        )
