    def _create_chat_completion_sdk(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Tuple[str, Optional[List[Dict]]]:
        """
        Create a chat completion using the native lmstudio-python SDK.
        
        Args:
            messages: List of message objects with role and content
            tools: Optional list of tools available to the model
            **kwargs: Additional parameters to pass to the SDK
        
        Returns:
            Tuple[str, Optional[List[Dict]]]: The model's response text and any tool calls
        
        Note: Tool calls are not directly supported by the LM Studio SDK.
              They are emulated through prompt engineering or ignored.
        """
        try:
            # Extract conversation context from messages
            prompt = ""
            system_message = None
            
            # First, find system message if it exists
            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                    break
            
            # Add system message first if it exists
            if system_message:
                prompt += f"System: {system_message}\n\n"
            
            # Add the conversation history
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                # Skip system message as it's already been handled
                if role == "system":
                    continue
                    
                role_prefix = "User: " if role == "user" else "Assistant: " if role == "assistant" else f"{role.capitalize()}: "
                
                if content:
                    prompt += f"{role_prefix}{content}\n"
            
            # Add prompt for assistant response
            prompt += "Assistant: "
            
            # If tools are provided, add them to the prompt
            if tools:
                tool_desc = "\nAvailable tools:\n"
                for tool in tools:
                    tool_desc += f"- {tool.get('name', '')}: {tool.get('description', '')}\n"
                prompt = f"{tool_desc}\n{prompt}"
            
            try:
                # Try generate method first
                try:
                    response = self._lmstudio_client.llm.generate(
                        prompt=prompt,
                        temperature=kwargs.get("temperature", 0.7),
                        max_tokens=kwargs.get("max_tokens", 1024),
                        **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
                    )
                    return response.text if hasattr(response, 'text') else str(response), None
                except AttributeError:
                    # Fallback to respond method
                    logger.info("generate method not available, falling back to respond")
                    response = self._lmstudio_client.llm.respond(prompt)
                    return response if isinstance(response, str) else str(response), None
                    
            except Exception as e:
                logger.error(f"SDK method failed: {e}")
                # Try connecting to model again before falling back
                try:
                    self._lmstudio_client.llm.connect()
                    response = self._lmstudio_client.llm.generate(prompt=prompt)
                    return response.text if hasattr(response, 'text') else str(response), None
                except Exception as reconnect_error:
                    logger.error(f"Reconnection attempt failed: {reconnect_error}")
                    raise
                    
        except Exception as e:
            logger.error(f"Error in LM Studio SDK chat completion: {e}")
            # Fallback to OpenAI API
            logger.info("Falling back to OpenAI-compatible API")
            return self._create_chat_completion_openai(messages, tools, **kwargs)
