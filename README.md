# 🌟 AgentRadis - Your AI Companion 🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AgentRadis is an extensible AI agent system designed to interact with various tools while maintaining context awareness. It provides a flexible framework for building AI-powered applications with tool-calling capabilities, encapsulated in a beautiful and intuitive interface. ✨

<p align="center">
  <img src="docs/images/agent_radis_banner.png" alt="AgentRadis Banner" width="800"/>
</p>

## ✨ Features

- **🔧 Tool Integration**: Seamlessly integrate various tools like file saving, web search, and code execution
- **🖥️ Multiple Interfaces**: Access via web UI, command line, or API
- **🧩 Flexible Framework**: Build custom agents with specific tool capabilities
- **🧠 Context Awareness**: Maintains conversation history and tool state
- **🛡️ Error Handling**: Robust error handling with informative feedback
- **🚀 MCP Server Support**: Install and use Model Context Protocol (MCP) servers for expanded capabilities
- **🎨 Beautiful UI**: Enhanced ASCII banner, formatted output, and user-friendly displays
- **🔄 Real-time Updates**: Live progress tracking and status updates
- **📝 Smart Planning**: Intelligent task planning and execution

## 🚀 Getting Started

### 📋 Prerequisites

- Python 3.9 or newer
- pip package manager
- Node.js and npm (for MCP server support)

### 🛠️ Installation

We provide two installation methods:

#### Method 1: Using conda 🐍

1. Create a new conda environment:

```bash
conda create -n agent_radis python=3.12
conda activate agent_radis
```

2. Clone the repository:

```bash
git clone https://github.com/scooter-lacroix/AgentRadis.git
cd AgentRadis
```

3. Install dependencies:

```bash
pip install -e .  # Install in editable mode
```

#### Method 2: Using venv 🔄

1. Clone the repository:

```bash
git clone https://github.com/scooter-lacroix/AgentRadis.git
cd AgentRadis
```

2. Run the setup script:

```bash
./run.sh
```

The script will automatically:
- Create a virtual environment if it doesn't exist
- Activate the environment
- Install all dependencies
- Start AgentRadis in interactive mode

### ⚙️ Configuration

AgentRadis requires configuration for the LLM APIs it uses. Follow these steps to set up your configuration:

1. Create a `config.toml` file in the `config` directory (you can copy from the example):

```bash
cp config/config.example.toml config/config.toml
```

2. Edit `config/config.toml` to add your API keys and customize settings:

```toml
# Global LLM configuration
[llm]
model = "gpt-4"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Replace with your actual API key
max_tokens = 4096
temperature = 0.0

# Optional configuration for specific LLM models
[llm.vision]
model = "gpt-4"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Replace with your actual API key
```

## 🚀 Quick Start

### 💻 Command Line Options

The `run.sh` script provides several ways to interact with AgentRadis:

```bash
# Show help and available options
./run.sh --help

# Start with web interface (default port 5000)
./run.sh --web

# Start API server only
./run.sh --api

# Show current configuration
./run.sh --config

# Run in flow execution mode with a prompt
./run.sh --flow "create a file"

# Process a prompt directly
./run.sh "search for cats"

# Interactive mode (default if no arguments)
./run.sh
```

### 🌐 Web Interface

Start the web interface:

```bash
./run.sh --web
```

Then open your browser at `http://localhost:5000`. The web interface provides:
- Real-time interaction with AgentRadis
- Tool execution visualization
- Command history
- Context-aware responses

### 🔄 Flow Mode

Flow mode is a special execution mode that allows for:
- Step-by-step task execution
- Better error handling
- Progress tracking
- Tool state management

Example:
```bash
./run.sh --flow "create a Python script that downloads images"
```

## 🏗️ Architecture

AgentRadis is built with a modular architecture:

- **🤖 Radis Agent**: Core agent that processes prompts and manages tools
- **🔧 Tool Interface**: Standardized way to define and interact with tools
- **🔌 API Layer**: FastAPI-based REST API for programmatic access
- **🎨 Web Interface**: User-friendly interface for interacting with the agent

## 🛠️ Available Tools

- **📁 file_saver**: Save content to files on the system
- **🔍 web_search**: Search the web for information
- **🐍 python_execute**: Execute Python code
- **🌐 browser_use**: Navigate and extract data from websites
- **💻 terminal**: Execute terminal commands
- **🐚 bash**: Execute bash scripts
- **📦 mcp_installer**: Install and manage MCP servers

## 🔧 Extending AgentRadis

### Adding New Tools 🛠️

Create a new tool by implementing the `Tool` interface:

```python
from app.tool.base import Tool

class MyCustomTool(Tool):
    name = "my_custom_tool"
    description = "Description of what your tool does"
    
    async def run(self, **kwargs):
        # Implement your tool logic
        return "Result of tool execution"
```

Then register your tool with the agent:

```python
from app.agent.radis import Radis

agent = Radis()
agent.add_tool(MyCustomTool())
```

## 🙏 Acknowledgements

AgentRadis draws inspiration from these outstanding projects:

- [Open Manus](https://github.com/mannaandpoem/OpenManus) - An extensible AI agent system
- [crawl4ai](https://github.com/openmapai/crawl4ai) - A web crawling framework for AI
- [pixiv_ai](https://github.com/pixiv/pixiv-ai) - AI agent framework by Pixiv

## 👨‍💻 Author

**Stanley Chisango** (@scooter-lacroix)
- 📧 Email: theslick.stan@gmail.com
- 🌐 GitHub: [scooter-lacroix](https://github.com/scooter-lacroix)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Star Us!

If you find AgentRadis helpful, please consider giving us a star on GitHub! It helps us grow and improve the project.
