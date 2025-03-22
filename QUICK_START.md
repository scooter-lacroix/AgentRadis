# AgentRadis Quick Start Guide

Welcome to AgentRadis! This guide will help you get up and running quickly with the system's powerful features.

## Installation

### Option 1: Quick Start with run.sh

```bash
git clone https://github.com/scooter-lacroix/AgentRadis.git
cd AgentRadis
./run.sh
```

This will automatically:
- Create a virtual environment
- Install required dependencies 
- Start AgentRadis in interactive mode

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/scooter-lacroix/AgentRadis.git
cd AgentRadis

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run AgentRadis
python main.py
```

## Configuration

1. Create your configuration file:

```bash
cp config/config.example.toml config/config.toml
```

2. Edit the configuration file to add your API keys and customize settings:

```bash
nano config/config.toml  # Or use any text editor
```

3. At minimum, set up your LLM provider information:

```toml
[llm]
model = "gpt-4"
base_url = "https://api.openai.com/v1"
api_key = "your-api-key-here"
```

## Running AgentRadis

### Command Line Options

```bash
# Basic interactive mode
./run.sh

# Start web interface
./run.sh --web

# Launch API server only
./run.sh --api

# Display configuration
./run.sh --config

# Execute a single command
./run.sh "create a python script to download images from Unsplash"

# Run in flow execution mode
./run.sh --flow "help me solve a math problem"
```

## Core Features

### Web Interface

Start the web interface:

```bash
./run.sh --web
```

Then access it at [http://localhost:5000](http://localhost:5000)

The interface provides:
- Chat-style interaction
- Tool execution visualization
- File uploads and downloads
- Voice interaction capabilities
- Command history

### API Access

Access the AgentRadis API for integration with other applications:

```bash
# Start the API server
./run.sh --api
```

Example API request:

```bash
curl -X POST http://localhost:5001/api/v1/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the weather in New York?", "mode": "chat"}'
```

## Working with Tools

AgentRadis comes with many built-in tools. Here are some common usage examples:

### Web Search

```
Search for the latest news about artificial intelligence
```

### File Operations

```
Create a file called hello.py with a simple hello world program
```

```
Read the content of file.txt and summarize it
```

### Python Code Execution

```
Run this code: print("Hello from Python")
```

### String Manipulation

```
Replace all occurrences of "old" with "new" in the file example.txt
```

### Voice Interaction

Enable voice interaction in the web interface by clicking the microphone icon, or use direct voice commands:

```
Listen to my voice and transcribe what I say
```

```
Speak this text: "Hello, I am AgentRadis, your AI assistant"
```

## Advanced Usage

### Creating Custom Tools

You can extend AgentRadis with custom tools. Create a Python file in the `app/tool` directory:

```python
from app.tool.base import BaseTool

class MyCustomTool(BaseTool):
    name = "my_custom_tool"
    description = "Description of what your tool does"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Description of parameter"
            }
        },
        "required": ["param1"]
    }
    
    async def run(self, **kwargs) -> dict:
        # Implement your tool logic
        param1 = kwargs.get("param1")
        result = f"Processed {param1}"
        return {
            "status": "success", 
            "result": result
        }
```

### Using the MCP App Store

The MCP App Store provides additional capabilities:

```
Show me available MCP apps
```

```
Install the image_processing MCP app
```

```
Use the image_processing app to resize my-image.jpg to 800x600
```

## Troubleshooting

If you encounter issues:

1. Check your configuration file for errors
2. Ensure API keys are valid
3. Look at the logs in `logs/agent.log`
4. Check terminal output for error messages
5. Try running with debug logging:

```bash
./run.sh --debug "your prompt here"
```

## Best Practices

- Use clear, specific instructions for best results
- Break complex tasks into smaller steps
- If a tool fails, try different phrasing or approach
- For file operations, use absolute paths when possible
- Run `./run.sh --config` to verify your configuration

## Getting Help

For additional help:

- Check the full documentation in the docs/ directory
- Join our community at [Discord](#)
- File issues on GitHub

Happy exploring with AgentRadis! 