from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """
    Base class for all tools in the system.
    
    All tools should inherit from this class and implement the required methods.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the tool.
        
        This name is used to register and lookup the tool in the tool registry.
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Returns a description of what the tool does.
        
        This description is used to provide information about the tool's functionality.
        """
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        Returns a dictionary of parameters the tool accepts.
        
        This is typically a JSON schema describing the expected input parameters.
        """
        pass
    
    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """
        Executes the tool's functionality asynchronously.
        
        Args:
            **kwargs: Parameters to pass to the tool execution.
            
        Returns:
            The result of the tool execution.
        """
        pass
    
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Synchronous interface for tool execution.
        
        By default, this provides a blocking wrapper around the async run method.
        Tools may override this for special synchronous behavior.
        
        Args:
            *args: Positional arguments to pass to the tool.
            **kwargs: Keyword arguments to pass to the tool.
            
        Returns:
            The result of the tool execution.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run(**kwargs))
    
    def reset(self) -> None:
        """
        Resets the tool's state.
        
        This method should be implemented by tools that maintain state
        between executions that needs to be reset.
        
        By default, this method does nothing.
        """
        pass

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """
    Base class for all tools in the system.
    All tools should inherit from this class and implement the required methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the tool.
        This name is used for tool registration and invocation.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Returns the description of the tool.
        This description is used to help understand what the tool does.
        """
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        Returns the parameters schema for the tool in JSON Schema format.
        This defines what parameters the tool accepts and their types.
        """
        pass

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """
        Executes the tool with the provided parameters.
        This is the async implementation of the tool's functionality.

        Args:
            **kwargs: Parameters for the tool execution.

        Returns:
            Any: The result of the tool execution.
        """
        pass

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Synchronous execution method for the tool.
        By default, this raises an error, but subclasses can override it
        to provide synchronous execution capabilities.

        Args:
            *args: Positional arguments for the tool execution.
            **kwargs: Keyword arguments for the tool execution.

        Returns:
            Any: The result of the tool execution.
        """
        raise NotImplementedError(
            f"Tool {self.name} does not support synchronous execution"
        )

    def reset(self) -> None:
        """
        Resets the tool's state.
        This is called when the tool needs to be reset between executions.
        By default, this does nothing, but subclasses can override it.
        """
        pass

