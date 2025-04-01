                    start_time = time.time()
                    try:
                        result = await self._execute_tool_call(standardized_call)
                        execution_time = time.time() - start_time
                        
                        # Process the result for better LLM consumption
                        result = self._process_tool_result(result, tool_name)
                        
                        results.append(f"Executed tool: {standardized_call.function.name}")
                        success = True

                        # Log successful execution metrics
                        self._log_tool_metrics(
                            tool_name=standardized_call.function.name,
                            success=True,
                            execution_time=execution_time,
                            tool_args=tool_args,
                            result=result,
                            error=None
                        )
                    except Exception as e:
                                f"Message: {detailed_error['message']}\n" +
                                f"Arguments: {detailed_error['args']}\n" +
                                f"Attempt: {detailed_error.get('attempt', 'N/A')}\n"
                    )
                    self.memory.add_message(error_context.role, error_context.content)

                    # Log failed execution metrics
                    error_traceback = traceback.format_exc()
                    execution_time = time.time() - start_time
                    self._log_tool_metrics(
                        tool_name=self._get_tool_name(command),
                        success=False,
                        execution_time=execution_time,
                        tool_args=tool_args,
                        result=None,
                        error=str(e),
                        error_traceback=error_traceback
                    )
    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()

    async def run(self, prompt: str, **kwargs) -> str:
