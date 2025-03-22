# AgentRadis Tool Examples

This document provides comprehensive examples of how to use all tools available in AgentRadis.

## Table of Contents

- [File Tools](#file-tools)
- [Web Tools](#web-tools)
- [Code Execution Tools](#code-execution-tools)
- [String Manipulation Tools](#string-manipulation-tools)
- [Speech Tools](#speech-tools)
- [Terminal Tools](#terminal-tools)
- [Planning Tools](#planning-tools)
- [System Tools](#system-tools)

## File Tools

### FileTool

The FileTool provides file system operations like reading, writing, and listing files.

#### Reading a file

```python
from app.tool import FileTool

file_tool = FileTool()
result = await file_tool.run(
    action="read",
    path="examples/sample.txt"
)

if result["status"] == "success":
    content = result["content"]
    print(f"File content: {content}")
else:
    print(f"Error: {result['message']}")
```

#### Writing a file

```python
result = await file_tool.run(
    action="write",
    path="examples/output.txt",
    content="Hello, AgentRadis!"
)

if result["status"] == "success":
    print("File written successfully")
else:
    print(f"Error: {result['message']}")
```

#### Listing directory contents

```python
result = await file_tool.run(
    action="list",
    path="examples/"
)

if result["status"] == "success":
    for item in result["items"]:
        print(f"{item['name']} - {'Directory' if item['is_dir'] else 'File'}")
else:
    print(f"Error: {result['message']}")
```

### FileSaver

FileSaver is specialized for saving content to files with additional features.

```python
from app.tool import FileSaver

saver = FileSaver()
result = await saver.run(
    filename="examples/data.json",
    content='{"key": "value", "array": [1, 2, 3]}',
    format="json",    # Optional: Will pretty-print if format is provided
    overwrite=True    # Will overwrite if file exists
)

if result["status"] == "success":
    print(f"File saved to {result['path']}")
else:
    print(f"Error: {result['message']}")
```

## Web Tools

### WebSearch

WebSearch allows searching across multiple search engines.

```python
from app.tool import WebSearch

search = WebSearch()
result = await search.run(
    query="AgentRadis AI assistant",
    engine="google",     # Options: google, bing, duckduckgo, brave
    num_results=5,
    language="en"
)

if result["status"] == "success":
    for item in result["results"]:
        print(f"Title: {item['title']}")
        print(f"URL: {item['url']}")
        print(f"Snippet: {item['snippet']}")
        print("---")
else:
    print(f"Error: {result['message']}")
```

### WebTool

WebTool provides advanced web browsing capabilities.

```python
from app.tool import WebTool

browser = WebTool()

# Navigate to a website
result = await browser.run(
    action="navigate",
    url="https://example.com"
)

# Extract content
result = await browser.run(
    action="extract",
    selector="h1"  # CSS selector
)

# Take screenshot
result = await browser.run(
    action="screenshot",
    output_path="examples/screenshot.png"
)

# Click on element
result = await browser.run(
    action="click",
    selector="button.submit"
)

# Fill form
result = await browser.run(
    action="fill",
    selector="input[name='query']",
    value="AgentRadis"
)

# Close browser when done
await browser.cleanup()
```

## Code Execution Tools

### PythonTool

PythonTool allows executing Python code safely.

```python
from app.tool import PythonTool

python = PythonTool()
result = await python.run(
    code="""
import math
import random

# Calculate prime factors
def prime_factors(n):
    factors = []
    d = 2
    while n > 1:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
        if d*d > n:
            if n > 1: 
                factors.append(n)
            break
    return factors

# Generate a random number and find its factors
number = random.randint(100, 1000)
factors = prime_factors(number)

print(f"Prime factors of {number} are: {factors}")
    """
)

if result["status"] == "success":
    print(f"Execution output: {result['output']}")
else:
    print(f"Error: {result['message']}")
```

## String Manipulation Tools

### StrReplaceEditor

StrReplaceEditor provides string replacement functionality with regex support.

```python
from app.tool import StrReplaceEditor

editor = StrReplaceEditor()

# Basic string replacement
result = await editor.run(
    action="replace",
    target_file="examples/sample.txt",
    pattern="hello",
    replacement="world",
    use_regex=False
)

if result["status"] == "success":
    print(f"Replacements made: {result['count']}")
else:
    print(f"Error: {result['message']}")

# Regex replacement
result = await editor.run(
    action="replace",
    target_file="examples/code.py",
    pattern=r"def (\w+)\(",
    replacement=r"def renamed_\1(",
    use_regex=True
)

if result["status"] == "success":
    print(f"Replacements made: {result['count']}")
else:
    print(f"Error: {result['message']}")

# Batch replacement across multiple files
result = await editor.run(
    action="batch_replace",
    target_glob="examples/*.txt",
    pattern="error",
    replacement="warning",
    use_regex=False
)

if result["status"] == "success":
    print(f"Files modified: {len(result['modified_files'])}")
    for file, count in result['modified_files'].items():
        print(f"- {file}: {count} replacements")
else:
    print(f"Error: {result['message']}")
```

## Speech Tools

### SpeechTool

SpeechTool provides speech recognition and synthesis.

```python
from app.tool import SpeechTool

speech = SpeechTool()

# Text-to-speech
result = await speech.run(
    action="speak",
    text="Hello, I am AgentRadis, your AI assistant!",
    voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
    speed=1.0       # Speed multiplier
)

if result["status"] == "success":
    print(f"Speech generated successfully: {result['audio_path']}")
else:
    print(f"Error: {result['message']}")

# Speech-to-text (from microphone)
print("Say something...")
result = await speech.run(
    action="listen",
    timeout=10.0,     # Maximum recording time in seconds
    language="en",    # Language code
    silence_threshold=0.1,  # Silence detection threshold
    silence_duration=1.0    # Silence duration to end recording
)

if result["status"] == "success":
    print(f"You said: {result['text']}")
else:
    print(f"Error: {result['message']}")

# Speech-to-text (from audio file)
result = await speech.run(
    action="transcribe",
    audio_path="examples/recording.wav",
    language="en"
)

if result["status"] == "success":
    print(f"Transcription: {result['text']}")
else:
    print(f"Error: {result['message']}")

# Clean up when done
await speech.cleanup()
```

## Terminal Tools

### TerminalTool

TerminalTool enables executing terminal commands.

```python
from app.tool import TerminalTool

terminal = TerminalTool()
result = await terminal.run(
    command="ls -la",
    working_dir="/home/user/project"  # Optional
)

if result["status"] == "success":
    print(f"Exit code: {result['exit_code']}")
    print(f"Output: {result['output']}")
else:
    print(f"Error: {result['message']}")

# Execute a command with timeout
result = await terminal.run(
    command="find / -name '*.py'",
    timeout=30  # Command will be terminated after 30 seconds
)

# Execute a shell script
result = await terminal.run(
    command="./scripts/backup.sh",
    env={"BACKUP_DIR": "/tmp/backup"}  # Environment variables
)
```

### BashTool

BashTool is specialized for bash script execution.

```python
from app.tool import BashTool

bash = BashTool()
result = await bash.run(
    script="""
    #!/bin/bash
    echo "Current directory:"
    pwd
    echo "Files:"
    ls -la
    echo "System info:"
    uname -a
    """,
    working_dir="/home/user/project"  # Optional
)

if result["status"] == "success":
    print(f"Exit code: {result['exit_code']}")
    print(f"Output: {result['output']}")
else:
    print(f"Error: {result['message']}")
```

## Planning Tools

### PlanningTool

PlanningTool helps break down complex tasks into manageable steps.

```python
from app.tool import PlanningTool
from app.agent import Radis

agent = Radis()
planning = PlanningTool(agent=agent)

result = await planning.run(
    task="Create a Python script that downloads images from a website and resizes them",
    max_steps=10,  # Maximum number of steps in the plan
    review=True    # Review plan before execution
)

if result["status"] == "success":
    print("Plan created and executed successfully")
    print(f"Steps executed: {len(result['executed_steps'])}")
    for i, step in enumerate(result['executed_steps']):
        print(f"Step {i+1}: {step['description']}")
        print(f"Result: {step['result']}")
else:
    print(f"Error: {result['message']}")
    if result.get('failed_step'):
        print(f"Failed at step: {result['failed_step']['description']}")
```

## System Tools

### ToolManager

ToolManager helps discover and manage available tools.

```python
from app.tool import ToolManager

manager = ToolManager()

# List all available tools
tools = await manager.run(action="list")
print("Available tools:")
for tool in tools["tools"]:
    print(f"- {tool['name']}: {tool['description']}")

# Get information about a specific tool
info = await manager.run(
    action="info",
    tool_name="web_search"
)
print(f"Tool info: {info}")

# Disable a tool
result = await manager.run(
    action="disable",
    tool_name="terminal"
)
print(f"Tool disabled: {result['status'] == 'success'}")
```

### ToolCollection

ToolCollection groups tools together for easier management.

```python
from app.tool import ToolCollection, WebSearch, FileTool, PythonTool

# Create a collection of research tools
research_tools = ToolCollection(
    WebSearch(),
    FileTool(),
    PythonTool()
)

# Use the tool collection with an agent
from app.agent import Radis
agent = Radis(available_tools=research_tools)

# Get tools as parameters for LLM function calling
tools_params = research_tools.to_params()
```

### CreateChatCompletion

CreateChatCompletion enables generating text completions from LLM models.

```python
from app.tool import CreateChatCompletion

chat = CreateChatCompletion()
result = await chat.run(
    prompt="Explain quantum computing in simple terms",
    model="gpt-4",  # Optional, defaults to config
    temperature=0.7,  # Optional
    max_tokens=500   # Optional
)

if result["status"] == "success":
    print(f"Response: {result['response']}")
else:
    print(f"Error: {result['message']}")
```

### Terminate

Terminate gracefully ends an agent session.

```python
from app.tool import Terminate

terminate = Terminate()
result = await terminate.run(
    reason="Task completed successfully",
    summary="Created files and analyzed data as requested"
)

print("Agent session terminated")
print(f"Reason: {result['reason']}")
print(f"Summary: {result['summary']}")
```

## Full Application Example

Here's a complete example that combines multiple tools:

```python
import asyncio
from app.agent import Radis
from app.tool import ToolCollection, WebSearch, FileSaver, PythonTool, StrReplaceEditor

async def main():
    # Create a tool collection
    tools = ToolCollection(
        WebSearch(),
        FileSaver(),
        PythonTool(),
        StrReplaceEditor()
    )
    
    # Initialize the agent with the tools
    agent = Radis(available_tools=tools)
    
    # Run a complex task
    result = await agent.run(
        "Search for information about recent advances in quantum computing, "
        "save the results to a file, create a Python script to analyze the "
        "frequency of keywords, and then replace all instances of 'computer' "
        "with 'quantum computer' in the results file."
    )
    
    print("Task execution complete!")
    print(f"Final response: {result}")
    
    # Close the agent
    await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Integration Examples

### Using the REST API

```python
import requests
import json

# Basic chat request
response = requests.post(
    "http://localhost:5001/api/v1/chat",
    json={
        "prompt": "Search for information about quantum computing",
        "stream": False
    },
    headers={"Authorization": "Bearer your-api-key"}
)
result = response.json()
print(f"Response: {result['response']}")

# Tool execution request
response = requests.post(
    "http://localhost:5001/api/v1/tool",
    json={
        "tool": "web_search",
        "params": {
            "query": "quantum computing advances 2024",
            "engine": "google"
        }
    },
    headers={"Authorization": "Bearer your-api-key"}
)
search_result = response.json()
print(f"Search results: {search_result['results']}")

# Streaming response
with requests.post(
    "http://localhost:5001/api/v1/chat",
    json={"prompt": "Write a long essay about AI", "stream": True},
    headers={"Authorization": "Bearer your-api-key"},
    stream=True
) as response:
    for line in response.iter_lines():
        if line:
            chunk = json.loads(line.decode('utf-8'))
            print(chunk["content"], end="", flush=True)
```

### Using the Python Client

```python
from agentradis_client import AgentRadisClient

# Initialize the client
client = AgentRadisClient(
    host="localhost", 
    port=5001,
    api_key="your-api-key"
)

# Chat completion
response = client.chat("Explain how neural networks work")
print(f"Response: {response}")

# Tool execution
results = client.execute_tool(
    tool_name="python_exec",
    code="import datetime; print(datetime.datetime.now())"
)
print(f"Execution result: {results}")

# File operations
client.save_file("example.txt", "This is a test file")
content = client.read_file("example.txt")
print(f"File content: {content}")

# Web search
results = client.search("latest AI research papers")
for result in results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print("---")

# Voice operations
audio_file = client.text_to_speech(
    "Hello, I am AgentRadis!",
    voice="alloy"
)
print(f"Audio saved to: {audio_file}")

# Cleanup the client when done
client.close()
``` 