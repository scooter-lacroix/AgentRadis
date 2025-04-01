    def __init__(self, tools: Optional[List[BaseTool]] = None, api_base: Optional[str] = None, planning_tool=None, **kwargs):
        """Initialize the agent with memory, state tracking, and tools"""
        super().__init__(**kwargs)
        
        # Core components
        self.memory = AgentMemory()
        self.state = AgentState.IDLE
        self._active_resources = []
        self.iteration_count = 0
        
        # Initialize tools
        self.tools = tools or []
        self.api_base = api_base
        self.planning_tool = planning_tool
        
        if not self.tools:
            self._initialize_tools()
        
        # Import time module for tool execution timing
        import time
        try:
            # For queries that don't need verification, try to answer with LLM's knowledge first
            direct_response = None
            if not needs_verification and mode != "plan":
                # Use LLM without tools first for non-verification queries
                logger.info("Attempting direct response without tools for query that doesn't need verification")
                try:
                    # Only pass system prompt if it's not already in the messages
                    system_msgs = None
                    if self.system_prompt and not any(m.role == Role.SYSTEM for m in self.memory.messages):
                        system_msgs = [Message(role=Role.SYSTEM, content=self.system_prompt)]
                    
                    # Call LLM without tools to test if it can answer from its knowledge
                    direct_response = await self.llm.ask(\
            # Check max iterations
            if self.iteration_count >= max_iterations:
                raise MaxIterationsException(max_iterations)
            
            # Check if we have a final response or need to continue
            if self.state == AgentState.THINKING:
                # Get the last assistant message
                assistant_messages = [m for m in self.memory.messages if m.role == Role.ASSISTANT and m.content]
                if assistant_messages and not assistant_messages[-1].tool_calls:
                    # If we have a response without tool calls, we're done
                    self.state = AgentState.DONE
                    break
            
            # Continue if we need more iterations
            if self.state != AgentState.DONE:
                continue
                
            break
        
            # If we have a direct response and didn't need to use tools, return it
            if direct_response is not None and not self.verification_mode:
                try:
                    return {
                        "response": direct_response,
                        "status": "success"
                    }
                except Exception as e:
                    logger.error(f"Error processing direct response: {str(e)}")
                    return {
                        "response": "Error processing direct response",
                        "status": "error",
                        "error": str(e)
                    }
        except MaxIterationsException as e:
            logger.error(f"Max iterations exceeded: {e}")
            return {
                "response": f"I apologize, but I've exceeded the maximum allowed iterations ({e}). Please try rephrasing your question.",
                "status": "error",
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error during run: {e}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "status": "error",
                "error": str(e)
            }

        # If we get here, generate and return the final response
        try:
            final_response = self._generate_final_response()
            return {
                "response": final_response,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            return {
                "response": "Error generating final response",
                "status": "error",
                "error": str(e)
            }
