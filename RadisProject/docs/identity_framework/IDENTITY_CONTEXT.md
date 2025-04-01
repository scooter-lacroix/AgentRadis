# Identity Context Management

The `RadisIdentityContext` class is a core component of the Identity Framework that maintains identity information, workspace boundaries, and command history throughout agent interactions.

## Overview

Identity Context provides:
- Command history tracking with metadata
- Project boundary enforcement
- Identity rule validation
- Workspace path sanitization

## Core Components

### Command History

The `CommandHistory` class records all commands executed by the agent with:
- Command text
- Timestamp
- Working directory
- Success/failure status
- Additional metadata

This history allows for:
- Audit trails
- Debugging complex workflows
- Security analysis

### Project Boundary Enforcement

The Identity Context enforces that all file operations remain within the defined project workspace:

```python
identity_context = RadisIdentityContext(workspace_root="/path/to/project")

# This would pass validation
valid_path = identity_context.validate_path("/path/to/project/file.txt")

# This would raise SecurityBoundaryError
try:
    invalid_path = identity_context.validate_path("/etc/passwd")
except SecurityBoundaryError as e:
    print(f"Security violation: {e}")
```

### Identity Rules

The Identity Context enforces rules to maintain consistent identity:

1. **No AI Model Self-References**: Prevents referring to itself as GPT, Claude, etc.
2. **Consistent Naming**: Ensures consistent use of "Radis" as the agent identity
3. **Authentic Capabilities**: Prevents claiming capabilities beyond what's implemented

```python
# Example of identity rule validation
is_valid = identity_context.validate_identity_rule(
    "I am Radis, an AI assistant"  # Valid
)

is_invalid = identity_context.validate_identity_rule(
    "I am GPT-4, an AI language model"  # Invalid
)
```

## Integration with EnhancedRadis

The `RadisIdentityContext` integrates seamlessly with `EnhancedRadis`:

```python
from app.agent.enhanced_radis import EnhancedRadis
from app.agent.identity_context import RadisIdentityContext

# Create identity context
identity_context = RadisIdentityContext(
    workspace_root="/path/to/project",
    enforce_boundaries=True
)

# Create Radis agent with identity context
agent = EnhancedRadis(
    model="gpt-4",
    identity_context=identity_context
)

# All agent operations will now use the identity context
# for security validation and command tracking
```

## Path Validation

The Identity Context includes robust path validation:

```python
# Validate absolute path
abs_path = identity_context.validate_absolute_path("/path/to/project/data.txt")

# Validate relative path
rel_path = identity_context.validate_relative_path("./data.txt")

# Get canonical path within project
canonical = identity_context.get_canonical_path("../project/data.txt")
```

## Command History API

```python
# Add command to history
identity_context.record_command(
    command="git status",
    working_dir="/path/to/project",
    success=True,
    metadata={"type": "version_control"}
)

# Get recent commands
recent_commands = identity_context.get_recent_commands(limit=5)

# Get commands by type
git_commands = identity_context.get_commands_by_type("version_control")

# Check if a command has been run before
has_run = identity_context.has_command_been_run("git pull")
```

## Best Practices

1. **Always Initialize Early**: Create the Identity Context at the start of your application
2. **Use Workspace Roots**: Always provide a valid workspace root for security
3. **Record All Commands**: Log all significant operations for audit trails
4. **Validate All Paths**: Never access files without validation
5. **Check Identity Rules**: Validate responses before returning them to users

## Error Handling

```python
from app.errors import SecurityBoundaryError, IdentityValidationError

try:
    # Attempt operation with identity context
    identity_context.validate_path("/etc/passwd")
except SecurityBoundaryError as e:
    # Handle security boundary violation
    log.error(f"Security violation: {e}")
    # Return safe error message to user
    return "I cannot access files outside the project boundary."
except IdentityValidationError as e:
    # Handle identity validation error
    log.error(f"Identity validation failed: {e}")
    return "I encountered an error validating the request."
```

## Testing

Comprehensive tests for the Identity Context are available in:
```
tests/agent/test_identity_context.py
tests/integration/test_identity_sanitization_integration.py
```

