# RadisProject Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Centralized tool registry management in `app/core/tool_registry.py`:
  - Implemented thread-safe singleton pattern for global tool management
  - Added performance metrics tracking for tool operations
  - Enhanced error handling with specialized exceptions
  - Added comprehensive logging for debugging and monitoring
  - Introduced robust parameter validation for tool registration
- Deprecated `app/tool/registry.py` in favor of `app.core.tool_registry`:
  - Added clear deprecation warnings with migration guidance
  - Maintained backward compatibility through wrapper implementation
  - Streamlined tool registration process with improved error reporting
  - Provided seamless transition path for existing code

### Migration Guide
To migrate to the new tool registry:
1. Update imports to use `from app.core.tool_registry import get_tool_registry`
2. Replace direct ToolRegistry instantiation with get_tool_registry()
3. Update error handling to catch new exception types (ToolNotFoundError, ToolRegistryError)
4. Remove any instance-specific tool registry creation in favor of the global singleton

### Fixed
- Fixed async/await usage in EnhancedRadis context manager:
  - Replaced synchronous __enter__ and __exit__ with async __aenter__ and __aexit__
  - Properly implemented asynchronous cleanup in __aexit__
  - Updated test files to use async context manager pattern
  - Ensured proper awaiting of cleanup operations in context manager
- Enhanced API connectivity and error handling infrastructure:
  - Implemented robust API connectivity check with comprehensive error reporting
  - Fixed cleanup resource handling to use proper agent cleanup method
  - Added enhanced error responses for API connectivity issues with clear user feedback
  - Improved error logging and diagnostic capabilities for API-related issues
- Fixed FlowFactory.create_flow() method call in run_flow.py:
  - Resolved incorrect usage of static method vs instance method
  - Updated code to properly instantiate FlowFactory first
  - Modified parameters to match correct method signature
  - Ensured proper context passing through initial_context parameter

### Changed
- Optimized context manager architecture in `app/core/context_manager.py` for improved performance and maintainability:
  - Enhanced thread synchronization mechanisms
  - Improved error handling and logging strategy
- Enhanced tool registry functionality in `app/core/tool_registry.py`:
  - Refined tool registration logic with parameter validation
  - Improved error handling for duplicate registrations
  - Added comprehensive logging for debugging
- Memory system optimizations:
  - Restructured memory management for better performance
  - Enhanced state persistence mechanisms
  - Improved integration with context management

### Added
- Enhanced session memory handling:
  - Improved token management for different LLM models
  - Optimized message history tracking with dynamic token limits
  - Added thread-safe operations for concurrent memory access
- Advanced context management features:
  - Implemented robust context flow control in context_manager.py
  - Added comprehensive error handling for context-related operations
  - Introduced new context validation mechanisms

### Fixed
- Enhanced RadisAgent to improve context awareness capabilities:
  - Fixed timestamp duplication in diagnostic logs for better debugging visibility
  - Improved method structure and code organization for better reliability
  - Reorganized schema imports to ensure proper typing and interface consistency
  - Enhanced dynamic tool invocation to work with multiple tools based on context
  - Enabled system to properly invoke planning and web search tools simultaneously when required
  - Fixed proper schema imports organization to prevent deprecation warnings
  - Ensured reliable tool method structure for consistent parameter passing
- Added proper display of ASCII banner and system introduction when starting the application in interactive mode by calling appropriate display functions in main.py
- Fixed critical issues in the planning tool implementation:
  - Resolved syntax errors with unclosed curly braces in the `_execute_step` method
  - Corrected indentation of `cleanup` and `reset` methods to properly be part of the PlanningTool class
  - Removed duplicated `_execute_step` method implementation
  - Successfully verified fixes by passing all planning tool tests

### Changed
- Improved RadisAgent architecture to enable more reliable context-aware operations:
  - Enhanced context handling to better support multi-tool workflows
  - Updated diagnostic logging to provide accurate timestamps and error reporting
  - Refined error handling to capture and report issues during tool execution
  - Strengthened tool invocation logic to ensure proper tool selection based on context

## LM Studio Integration Update - March 30, 2025

### Successfully Implemented Direct LM Studio Integration

- Created a new `LMStudioDirect` client that uses the working `/v1/chat/completions` endpoint
- Successfully tested with the Qwen 2.5 7B Instruct model in LM Studio
- Achieved proper prompt handling and response processing
- Integrated with RadisAgent framework for consistent user experience

This implementation properly sends user prompts to LM Studio's language model
and returns the responses through RadisProject's infrastructure. The prompts
are sent directly to the model, processed, and the responses are returned to 
the user, fulfilling the requirement for actual model inference rather than
hardcoded responses.

Extended testing confirms successful completion of requests with detailed
responses generated by the language model, not pre-programmed outputs.

### Technical Implementation

- Direct HTTP client bypasses OpenAI library compatibility issues
- Properly formatted JSON requests to the `/v1/chat/completions` endpoint
- Robust error handling for network and API issues
- Command-line runner with comprehensive options

### Future Improvements

- Further integration with Radis tools and capabilities
- Support for streaming responses
- Improved context handling for multi-turn conversations

## LM Studio WebSocket URL Fix - March 30, 2025

### Overview
Fixed an issue in the LMStudioClient class where WebSocket URLs were incorrectly formed with double protocols (e.g., `ws://http://localhost:1234/llm` instead of `ws://127.0.0.1:1234/llm`), preventing successful WebSocket connections.

### Detailed Changes

#### 1. Fixed Host:Port Extraction in _initialize_clients
  - Fixed indentation issues in the _initialize_clients method
  - Enhanced the host:port extraction logic from API base URLs
  - Added more robust handling for URLs with or without protocol prefixes
  - Ensured the lmstudio.Client is only created with the host:port portion

#### 2. WebSocket URL Formation Improvement
  - Modified the code to properly extract only the host:port part from api_base URLs
  - Prevented double protocol prefixes in WebSocket URLs (e.g., `ws://http://`)
  - Added fallback with protocol stripping for cases where regex doesn't match
  - Added clear logging to indicate which host:port is being used

#### 3. Code Structure Improvements
  - Fixed indentation inconsistencies in the _initialize_clients method
  - Correctly nested all initialization logic within proper code blocks
  - Maintained existing model loading logic with llm.connect()
  - Improved error handling for client initialization

### Testing and Verification
- Created test script to verify proper WebSocket URL formation
- Confirmed WebSocket connections are successfully established
- Tested with both protocol-prefixed and non-prefixed API base URLs
- Verified that all LM Studio client functionality works with the fix

### Changed Code
```python
# Before (problematic):
# host_port = self.api_base.rstrip('/')
# self._lmstudio_client = lmstudio.Client(api_host=host_port)

# After (fixed):
host_port_pattern = re.compile(r'(?:https?://)?([^/]+)')
match = host_port_pattern.search(self.api_base)
if match:
    host_port = match.group(1)
else:
    # Fallback with explicit protocol stripping
    host_port = self.api_base.replace('http://', '').replace('https://', '').rstrip('/')

self._lmstudio_client = lmstudio.Client(api_host=host_port)
```

## ROCm Compatibility Improvement - March 29, 2025

### Overview
Fixed an issue with ROCm initialization and GradScaler usage in the optimized_radis.py module to improve compatibility with AMD GPUs and eliminate errors when CUDA is not available.

### Detailed Changes

#### 1. Fixed GradScaler Initialization and Handling
  - Modified the GradScaler initialization to be properly nested within ROCm detection and initialization
  - Changed scaler initialization to use parameter 'device_type="cuda"' for proper compatibility
  - Added null checks before using the scaler to prevent errors when CUDA/ROCm is not available
  - Fixed indentation issues in the `_initialize_rocm()` method
  - Improved error handling for GradScaler initialization failures

#### 2. Improved Error Handling for Non-GPU Environments
  - Added graceful fallback when GradScaler initialization fails
  - Added logging of initialization failures to aid in debugging
  - Ensured the application can continue running even if the GradScaler is not available
  - Added exception handling with informative error messages

#### 3. Code Structure Improvements
  - Fixed indentation inconsistencies in the ROCm initialization code
  - Restructured the nested try-except blocks for better readability and maintainability
  - Added clear logging messages at each initialization step
  - Improved code organization to make future maintenance easier

### Testing and Verification
- Command: `python -m pytest -vW error::DeprecationWarning -vW error::FutureWarning`
- Result: All 25 tests pass in 1.67s without any warnings

### Configuration Changes
- **GradScaler Initialization**
  - Before: `self.scaler = GradScaler('cuda')`
  - After: `self.scaler = GradScaler(device_type="cuda")`

- **Error Handling**
  - Before: Limited exception handling, no null checks for scaler
  - After: Comprehensive try-except blocks with proper logging and null checks

- **Indentation Structure**
  - Before: Inconsistent indentation in _initialize_rocm() method
  - After: Properly structured indentation with clear logical flow

## Code Modernization and API Updates - March 29, 2025
Updated the codebase to replace deprecated methods and implement the new message handling system, ensuring compatibility with the updated tool registry and context management systems.

### Detailed Changes

#### 1. Tool Registry Updates
  - Updated tool registration from `register_tool(tool_instance=tool)` to `register_tool(tool_name, tool)`
  - Changed from `get_tool_names()` to `list_tools()`
  - Updated MockTool with `execute()` method
  - Fixed imports to use `app.core.tool_base`

#### 2. Memory System Modernization
  - Replaced dictionaries with proper `Message` class objects
  - Updated from `conversation_history` to `messages`
  - Added imports for `Message` and `Role`

#### 3. Context Management Changes
  - Updated from `initialize_context()` to `get_or_create_context()`
  - Fixed context retrieval in tests

### Testing
  - Updated all tests to work with new API patterns
  - Verified compatibility between components

## Identity Framework Implementation - March 28, 2025

### Added
- Identity sanitization framework components:
  - `ResponseProcessor` class for detecting and replacing model references
  - `ModelNameDetector` for AI model reference identification
  - `PathValidator` for secure file path operations
  - `RadisIdentityContext` for maintaining identity consistency

- Security boundaries implementation:
  - Project boundary enforcement for working directory changes
  - Path validation and sanitization for secure file access
  - Command history tracking with success/failure status
  - Security rule enforcement for all operations

- Response processing features:
  - Automatic detection and replacement of AI model references
  - Consistent "Radis" identity maintenance across responses
  - Tool output sanitization for consistent identity presentation
  - Robust error handling for malformed responses

### Fixed
- Parameter signature compatibility in tool invocations:
  - Updated EnhancedRadis to use keyword arguments when calling tool.run()
  - Changed direct tool.run(prompt) to tool.run(prompt=prompt) for consistent parameter passing
  - Verified correct usage of run() method across all implementations
- Verified correct implementation of rich.box.DOUBLE usage in display.py

### Improved
- Enhanced Radis agent with identity context integration
- Signal handling for graceful shutdown and resource cleanup
- Error management with specialized error classes
- Type validation for incoming JSON requests
- Backward compatibility with existing methods

### Documentation
- Created comprehensive documentation in `docs/identity_framework/`
- Added usage examples and integration guidelines
- Documented security boundaries and best practices
- Provided detailed API references for all components

### Testing
- Added unit tests for all Identity Framework components
- Created comprehensive integration tests for end-to-end validation
- Included test cases for error recovery and edge conditions
- Implemented test coverage for security boundary enforcement

## Identity Sanitization Framework Test Plan - March 28, 2025
- Created comprehensive test plan for Identity Sanitization Framework components:
  - Designed test scenarios for ResponseProcessor to verify self-reference detection and replacement
  - Developed test cases for RadisIdentityContext class to validate identity reference enforcement
  - Established integration test suite for EnhancedRadis to ensure consistent identity maintenance
  - Created edge case tests for complex nested identity references and path traversal attempts
  - Added performance evaluation metrics to measure sanitization impact
  - Implemented test scripts for security boundary validation across all framework components
  - Developed thread safety and concurrency tests to verify proper isolation between contexts
  - Created a detailed implementation plan for adding tests to the existing codebase

### Implementation Progress - Identity Sanitization Framework

#### Completed Steps

1. Created ResponseProcessor [app/agent/response_processor.py]
  - ✓ Implemented core class with identity sanitization logic
  - ✓ Added methods for detecting incorrect self-references
  - ✓ Added regex-based detection for model names
  - ✓ Implemented sanitization logic to replace with "Radis"
  - ✓ Added comprehensive unit tests
2. Created RadisIdentityContext [app/agent/identity_context.py]
  - ✓ Implemented class for identity context management
  - ✓ Added methods for validating identity consistency
  - ✓ Added functionality for enforcing identity rules
  - ✓ Implemented conversation history tracking
  - ✓ Added methods for identity trend analysis
3. Updated EnhancedRadis [app/agent/enhanced_radis.py]
  - ✓ Integrated ResponseProcessor and RadisIdentityContext
  - ✓ Added identity sanitization to response processing
  - ✓ Applied identity checks to tool outputs
  - ✓ Fixed implementation issues and syntax errors

### Current Task
- Updating RadisAgent class to integrate identity components

### Pending Steps
1. Update remaining EnhancedRadis references (if any)
2. Modify LLM Interface [app/llm.py]
3. Update Tool Execution Framework
4. Final scope verification and testing

### Notes
- All modifications are being made within the "RadisProject" directory as specified
- Identity sanitization is being consistently applied across components
- Unit tests have been included where appropriate

## PlanningTool Implementation Progress - March 28, 2025

### Completed
- _generate_plan_with_agent implementation:
  - Added async implementation with proper type hints and validation
  - Integrated agent's generate_content for plan generation
  - Implemented comprehensive JSON parsing and validation
  - Added fallback to basic plan on parsing failures
  - Included detailed error handling and logging
  - Verified proper async/await usage and integration
  - Enhanced docstring with examples and error cases

### Implementation Gap Identified
- Discovered missing `_generate_plan_with_agent` method in PlanningTool:
  * Method referenced in run() but not implemented
  * Affects AI-driven plan generation functionality
  * Currently falls back to basic plan creation
  * Impacts integration tests and agent-based planning

### Implementation Plan
- PlanningTool Enhancement Requirements:
  * Add `_generate_plan_with_agent` method with proper async signature
  * Implement plan generation using agent capabilities
  * Add comprehensive error handling and validation
  * Include fallback mechanisms for robustness

### Technical Details
- Required Method Signature:
  * async def _generate_plan_with_agent(self, task: str, max_steps: int)
  * Returns List[Dict[str, str]] of structured plan steps
  * Integrates with agent's generate_content capability
  * Includes JSON response parsing and validation

### Validation Status
- Current Implementation:
  * Verified keyword argument handling in tool.run()
  * Confirmed basic plan generation works
  * Identified test adjustments needed
  * Documented parameter signature compatibility

## [2.0.0] - 2024-01-09

### Added
- New `ToolRegistry` component in `app/core/tool_registry.py`
  - Singleton pattern with thread-safe implementation
  - Tool validation using BaseTool's validate_parameters
  - Comprehensive tool registration and retrieval methods
  - Built-in metrics tracking for tool usage
  - Custom exceptions for better error handling
- New `ContextManager` in `app/core/context_manager.py`
  - Thread-safe context tracking system
  - Session state management integration
  - Methods for context updates and retrieval
- New `RollingWindowMemory` in `app/core/rolling_window_memory.py`
  - Fixed-size window implementation for conversation history
  - Efficient memory management with automatic cleanup
  - Thread-safe operations
  - Integration with session management
- Comprehensive integration tests in `app/tests/test_integration.py`
  - End-to-end testing of all new components
  - Validation of tool registration and execution
  - Context management testing
  - Memory integration testing

### Changed
- Major refactor of `EnhancedRadis` agent implementation
  - Replaced local tool list with global ToolRegistry
  - Integrated new ContextManager for state handling
  - Updated memory management to use new RollingWindowMemory
  - Enhanced cleanup procedures for resource management
- Improved tool validation system
  - Added mandatory parameter validation
  - Enhanced error reporting
  - Added tool existence checks

### Improved
- Thread safety across all components
- Resource management and cleanup procedures
- Error handling with custom exceptions
- Logging system for better debugging
- Tool validation and parameter checking
- Context persistence and management
- Memory management efficiency

### Migration Guide
To upgrade to version 2.0.0:

1. Update tool registration to use new ToolRegistry:
   ```python
   from app.core.tool_registry import ToolRegistry
   
   registry = ToolRegistry()
   registry.register_tool(your_tool)
   ```

2. Replace direct tool list usage with ToolRegistry methods
3. Update context handling to use new ContextManager
4. If using memory features, migrate to new RollingWindowMemory
5. Update cleanup procedures to include new component cleanup calls

### Notes
- All new components are thread-safe by default
- Existing security and identity context functionality remains intact
- The new architecture provides better scalability and maintainability
- Additional logging and metrics are available for debugging

## LM Studio Client Fix - April 10, 2025

### Fixed
- Fixed compatibility issues in the LM Studio client implementation:
  - Updated the `LMStudioClient` class to properly handle tool calls and API responses
  - Fixed parameter signatures to match test expectations
  - Added proper fallback mechanisms between SDK and OpenAI API implementations
  - Enhanced error handling and logging throughout the client
  - Made the client implementation more robust for different usage scenarios
  - Ensured proper handling of optional arguments and configuration parameters
  - Fixed compatibility with newer SDK versions and the OpenAI API
  - Wrapped model.respond() call in a try-except block to catch AttributeError and provide fallback to OpenAI-compatible API method, ensuring robust operation whether the SDK method is available or not

### Technical Implementation
- Improved class initialization with proper default parameters
- Enhanced SDK detection and usage with robust fallback mechanisms
- Fixed method signatures to match expected test patterns
- Updated response handling to properly return expected formats
- Ensured proper handling of the simplified API vs direct API approaches

### Testing
- Verified all tests pass with both SDK available and unavailable scenarios
- Ensured backward compatibility with existing code
- Improved error handling for edge cases
