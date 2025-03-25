# 🌟 AgentRadis - Your AI Companion 🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AgentRadis is an extensible AI agent system designed to interact with various tools while maintaining context awareness. It provides a flexible framework for building AI-powered applications with tool-calling capabilities, encapsulated in a beautiful and intuitive interface. ✨

<p align="center">
  <img src="docs/images/banner.txt" alt="AgentRadis Banner" width="800"/>
</p>

## ✨ Features

- **🔧 Tool Integration**: Seamlessly integrate various tools like file saving, web search, code execution, and string manipulation
- **🖥️ Multiple Interfaces**: Access via web UI, command line, or API
- **🧩 Flexible Framework**: Build custom agents with specific tool capabilities
- **🧠 Context Awareness**: Maintains conversation history and tool state
- **🛡️ Error Handling**: Robust error handling with informative feedback
- **🚀 MCP Server Support**: Install and use Model Context Protocol (MCP) servers for expanded capabilities
- **🎨 Beautiful UI**: Enhanced ASCII banner, formatted output, and user-friendly displays
- **🔄 Real-time Updates**: Live progress tracking and status updates
- **📝 Smart Planning**: Intelligent task planning and execution
- **🗣️ Voice Interaction**: Advanced speech recognition and synthesis capabilities
- **🔍 Robust Web Search**: Multi-engine search with comprehensive results
- **📄 Text Manipulation**: Powerful string editing and replacement capabilities
- **💻 Code Execution**: Safe and isolated Python code execution

## 🏗️ Revolutionary Architecture: The Brain Behind the Magic

AgentRadis isn't just another AI tool—it's a **complete cognitive ecosystem** built from the ground up for unparalleled versatility and power. Our cutting-edge architecture combines state-of-the-art AI with innovative engineering to create an experience that feels nothing short of magical.

<p align="center">
  <img src="docs/images/architecture.txt" alt="AgentRadis Architecture" width="700"/>
</p>

### 🧠 Four-Tier Intelligence Architecture

- **🌟 Brilliantly Adaptive Agent Layer**
  - **Radis Agent**: The crown jewel—our flagship general-purpose agent with advanced reasoning capabilities that adapts to virtually any task
  - **ToolCall Agent**: A specialized powerhouse that executes complex tool chains with unmatched precision
  - **Planning Agent**: Our strategic mastermind that breaks complex problems into perfectly orchestrated action plans
  - Each agent features our proprietary **Contextual Memory System™** that maintains perfect awareness of ongoing tasks

- **🛠️ Enterprise-Grade Tool Layer** 
  - Over 35+ specialized tools seamlessly integrated into a cohesive ecosystem
  - Modular design allows for infinite extensibility with zero friction
  - Real-time tool discovery and autonomous tool acquisition capabilities
  - Built-in automatic error handling and recovery protocols

- **🔌 Lightning-Fast API Layer**
  - Built on industrial-strength FastAPI for millisecond response times
  - WebSocket support for real-time bidirectional communication
  - Enterprise-ready authentication and rate limiting
  - Comprehensive API documentation with interactive examples

- **💎 Stunning Interface Layer**
  - Award-worthy responsive design that works flawlessly across all devices
  - Intelligent dark/light mode transitions based on user preferences
  - Real-time visualization of agent reasoning and tool execution
  - Voice-enabled interface with natural language processing

## 🛠️ Supercharged Tool Arsenal: Unlimited Possibilities

AgentRadis comes packed with a **breathtaking collection of tools** that transform what's possible with AI. Each tool is meticulously crafted for maximum performance and reliability, giving you capabilities that feel like superpowers.

### 🔥 Ultimate File Manipulation Suite
- **📁 FileTool**: Powerful file operations with military-grade security controls
- **📝 FileSaver**: Instant content saving with automatic formatting and versioning
- **🔍 FileSearch**: Lightning-fast file discovery across your entire system
- **📊 FileStat**: Comprehensive file analysis and visualization tools

### 🌐 Web Intelligence Center
- **🔎 WebSearch**: Multi-engine search capabilities that leave no stone unturned
- **🧠 WebExtract**: Advanced content extraction with semantic understanding
- **📸 WebCapture**: High-fidelity website captures with interactive elements
- **🔄 WebInteract**: Full browser automation for complex web tasks

### 💻 Code Execution Powerhouse
- **🐍 PythonTool**: Execute Python code within a secure sandboxed environment
- **⚡ JavaScriptTool**: Run JavaScript with full DOM interaction capabilities
- **📊 DataAnalysisTool**: Process and visualize complex datasets with a single command
- **🤖 AutomationTool**: Create sophisticated workflows with minimal code

### 🗣️ Advanced Communication Hub
- **🎤 SpeechTool**: State-of-the-art speech recognition and synthesis
- **🔊 AudioTool**: Comprehensive audio processing and analysis
- **📱 NotificationTool**: Multi-channel alerts and notifications
- **💬 ChatTool**: Engage with multiple LLM providers simultaneously

### 🧩 System Integration Masters
- **💻 Terminal**: Execute system commands with precision and safety
- **🐧 Bash**: Run complex bash scripts with rich output parsing
- **🔌 APITool**: Interact with external APIs with automatic authentication
- **📡 NetworkTool**: Comprehensive network diagnostics and management

## 🚀 Limitless Expansion: Beyond Imagination

AgentRadis isn't just a tool—it's a **living, growing ecosystem** designed to constantly evolve and expand. Our revolutionary architecture allows for unlimited customization and extension to meet any challenge you can imagine.

### 🧩 Build Your Dream Tools in Minutes

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
        # Process the parameter
        result = f"Processed {param1}"
        return {
            "status": "success", 
            "result": result
        }
        
    async def cleanup(self):
        # Clean up any resources
        pass
```

### 🌟 Autonomous Tool Discovery & Integration

AgentRadis takes extension to the next level with its **revolutionary MCP App Store integration**. Unlike any other AI system, AgentRadis can:

- **🧠 Autonomously identify when it needs additional capabilities** and request them from the MCP App Store
- **🔍 Dynamically discover new tools** based on the task at hand without human intervention
- **⚡ Install and integrate new tools in seconds**, making them immediately available
- **👨‍💻 Learn how to use new tools on the fly** with zero training required
- **🔄 Manage tool lifecycles automatically**, including updates and dependencies

Simply ask AgentRadis to perform a task requiring a specialized tool, and watch in amazement as it:

```
User: "Can you analyze the sentiment in these customer reviews?"

AgentRadis: "I'll analyze the sentiment in these customer reviews for you. I need to install a specialized tool for this task."

[AgentRadis automatically searches the MCP App Store]

AgentRadis: "I've found and installed the SentimentAnalyzer tool from the MCP App Store. Now I'll analyze your customer reviews..."

[Results appear moments later]
```

### 🔮 Custom Agents for Specialized Tasks

Create specialized agents tailored to specific domains with our intuitive extension framework:

```python
from app.agent.toolcall import ToolCallAgent
from app.tool import ToolCollection, WebSearch, FileSaver

class ResearchAgent(ToolCallAgent):
    name = "ResearchAgent"
    description = "Agent specialized in research tasks"
    available_tools = ToolCollection(
        WebSearch(),
        FileSaver()
    )
    system_prompt = "You are a research assistant focused on finding accurate information."
```

## 🗣️ Speech Capabilities

AgentRadis includes powerful speech recognition and synthesis capabilities:

### Speech Recognition
- Real-time speech-to-text conversion
- Multiple language support
- Configurable sensitivity and silence detection
- Local model support for privacy

### Speech Synthesis
- High-quality text-to-speech
- Multiple voice options (alloy, echo, fable, onyx, nova, shimmer)
- Speed and pitch control
- SSML support for advanced control

Example usage:
```python
from app.tool import SpeechTool

# Initialize the speech tool
speech = SpeechTool()

# Listen for speech
result = await speech.run(
    action="listen",
    timeout=10.0,
    language="en"
)
print(f"Heard: {result['text']}")

# Speak text
await speech.run(
    action="speak",
    text="Hello, I am AgentRadis!",
    voice="alloy"
)
```

## 🔍 Web Search Capabilities

AgentRadis includes a powerful web search system that:

- Supports multiple search engines (Google, Bing, DuckDuckGo, Brave)
- Combines results for comprehensive coverage
- Caches results to improve performance
- Handles rate limiting and errors gracefully
- Provides contextual snippets for better understanding
- Extracts structured data when available
- Supports image search capabilities

Example usage:
```python
from app.tool import WebSearch

# Initialize the web search tool
search = WebSearch()

# Perform a search
result = await search.run(
    query="latest developments in AI",
    engine="google",
    num_results=5
)

# Process results
for item in result["results"]:
    print(f"Title: {item['title']}")
    print(f"URL: {item['url']}")
    print(f"Snippet: {item['snippet']}")
    print("---")
```

## 📝 String Replacement Tool

The `StrReplaceEditor` tool provides powerful text manipulation capabilities:

- Basic string replacement
- Regular expression support
- File content manipulation
- Batch operations across multiple files
- Interactive mode for confirmation
- Undo/redo capability

Example usage:
```python
from app.tool import StrReplaceEditor

# Initialize the string replacement tool
editor = StrReplaceEditor()

# Replace in a single file
result = await editor.run(
    action="replace",
    target_file="example.txt",
    pattern="hello",
    replacement="world",
    use_regex=False
)
print(f"Replacements made: {result['count']}")

# Replace with regex
result = await editor.run(
    action="replace",
    target_file="code.py",
    pattern=r"def (\w+)\(",
    replacement=r"def renamed_\1(",
    use_regex=True
)
```

## 📊 Performance and Limits

- **Memory Usage**: Typically requires 150-500MB RAM
- **Disk Space**: ~200MB for core installation, additional space for cached data
- **API Rate Limits**: Respects provider rate limits with exponential backoff
- **Tool Execution**: Timeout protection for all tools (default 30s)
- **Python Execution**: Sandboxed with memory and time limits
- **Concurrent Operations**: Handles multiple simultaneous requests
- **Response Size**: Manages large responses with chunking and streaming

## 🔌 API Integration

AgentRadis provides a comprehensive API for integration with other applications:

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

## 🙏 Acknowledgements

AgentRadis draws inspiration from these outstanding projects:

- [Langchain](https://github.com/langchain-ai/langchain) - Framework for LLM applications
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) - An autonomous GPT-4 experiment
- [AgentGPT](https://github.com/reworkd/AgentGPT) - AI agents in your browser

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

AgentRadis offers extensive configuration options to customize its behavior and integrate with various LLM providers and tools. The system is designed to work with multiple LLM providers including OpenAI, Anthropic, Azure, Ollama, and LM Studio.

1. Create a `config.toml` file in the `config` directory (you can copy from the example):

```bash
cp config/config.example.toml config/config.toml
```

2. Edit `config/config.toml` to add your API keys and customize settings:

```toml
# Global LLM configuration
[llm]
model = "gpt-4"                # Main LLM model
base_url = "https://api.openai.com/v1"  # API endpoint
api_key = "sk-..."             # Your API key
max_tokens = 4096              # Maximum response length
temperature = 0.0              # Response randomness (0.0-2.0)
timeout = 60                   # API request timeout (seconds)
retry_attempts = 3             # Number of retry attempts on failure
streaming = true               # Enable streaming responses

# Vision model configuration
[llm.vision]
model = "gpt-4-vision-preview" # Vision-capable model
base_url = "https://api.openai.com/v1"
api_key = "sk-..."             # Can be different from main API key
max_tokens = 4096
detail_level = "high"          # Image detail level (low, medium, high)

# Alternative LLM providers
[llm.providers.anthropic]
enabled = false
model = "claude-3-opus-20240229"
api_key = ""

[llm.providers.azure]
enabled = false
model = "gpt-4"
api_key = ""
endpoint = "https://your-endpoint.openai.azure.com/"
api_version = "2023-05-15"

[llm.providers.local]
enabled = false                # Local LLM support
model = "llama3"               # Model name in Ollama or similar
endpoint = "http://localhost:11434/v1"

# MCP app store settings
[mcp]
enabled = true                 # Enable MCP app store
server_url = "http://localhost:5004"
install_dir = "./mcp_apps"
auto_update = true             # Automatically update MCP apps
verify_signatures = true       # Verify app signatures for security

# Speech tool settings
[speech]
enabled = true                 # Enable speech capabilities
stt_model = "tiny.en"          # Speech-to-text model (tiny.en, base.en, large)
stt_engine = "whisper"         # STT engine (whisper, faster_whisper)
tts_model = "tts-1"            # Text-to-speech model
tts_voice = "alloy"            # Voice to use (alloy, echo, fable, onyx, nova, shimmer)
auto_transcribe = false        # Automatically transcribe audio input
language = "en"                # Default language
sample_rate = 16000            # Audio sample rate
silence_threshold = 0.1        # Silence detection threshold
silence_duration = 1.0         # Silence duration to end recording (seconds)

# Web search configuration
[web_search]
enabled = true                 # Enable web search
default_engine = "google"      # Default search engine
engines = ["google", "bing", "duckduckgo", "brave"]
cache_results = true           # Cache search results
cache_ttl = 300                # Cache duration (seconds)
max_results = 10               # Maximum results per search
timeout = 30                   # Search timeout (seconds)
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Tool-specific settings
[tools]
allow_terminal = true          # Allow terminal commands
allow_python_exec = true       # Allow Python code execution
allow_file_access = true       # Allow file system access
show_hidden_files = false      # Show hidden files in file listings
sudo_allowed = false           # Allow sudo commands (use with caution)
max_file_size = 10485760       # Maximum file size to handle (10MB)
restricted_paths = ["/etc", "/var"]  # Paths restricted from access
allowed_python_modules = ["os", "sys", "re", "json", "requests", "numpy", "pandas"] # Allowed modules for Python execution

# Agent behavior settings
[agent]
max_steps = 100                # Maximum execution steps
memory_limit = 50              # Number of messages to keep in memory
tool_choice = "auto"           # Tool choice mode: auto, required, none
system_prompt = "You are a helpful AI assistant with access to various tools."
default_agent = "radis"        # Default agent type (radis, toolcall, planning)
timeout = 300                  # Agent session timeout (seconds)
verbose_logging = true         # Enable detailed logging
keep_history = true            # Maintain conversation history

# Web interface settings
[web]
enabled = true                 # Enable web interface
host = "0.0.0.0"               # Host to bind to
port = 5000                    # Port to listen on
debug = false                  # Enable debug mode
require_auth = false           # Require authentication
theme = "dark"                 # UI theme (dark, light)
max_upload_size = 52428800     # Maximum upload size (50MB)

# API settings
[api]
enabled = true                 # Enable API server
host = "0.0.0.0"               # Host to bind to
port = 5001                    # Port to listen on
debug = false                  # Enable debug mode
require_auth = true            # Require authentication
rate_limit = 100               # Requests per minute
cors_origins = ["http://localhost:3000", "https://yourapp.com"]

# Logging configuration
[logging]
level = "INFO"                 # Logging level (DEBUG, INFO, WARNING, ERROR)
log_file = "logs/agent.log"    # Log file location
max_size = 10485760            # Maximum log file size (10MB)
backup_count = 5               # Number of backup logs to keep
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

3. **Environment Variables Support**: As an alternative to the config file, you can use environment variables:

```bash
export RADIS_LLM_API_KEY="sk-your-key-here"
export RADIS_LLM_MODEL="gpt-4"
export RADIS_SPEECH_TTS_VOICE="alloy"
```

4. **Advanced Configuration**:
   - `config/tools.toml`: Configure available tools and their permissions
   - `config/prompts.toml`: Customize system prompts for different agent modes
   - `config/ui.toml`: Customize the user interface appearance

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
- File uploads and downloads
- Voice interaction capabilities
- Syntax highlighting for code

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

## 👨‍💻 Author

**Stanley Chisango** (@scooter-lacroix)
- 📧 Email: theslick.stan@gmail.com
- 🌐 GitHub: [scooter-lacroix](https://github.com/scooter-lacroix)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Star Us!

If you find AgentRadis helpful, please consider giving us a star on GitHub! It helps us grow and improve the project.

## New Features

### Speech Recognition and Synthesis

AgentRadis v2 now includes speech recognition and synthesis capabilities through the integration of RealtimeSTT and RealtimeTTS libraries. These capabilities are managed through the MCP App Store.

Features:
- Speech-to-text conversion
- Text-to-speech with different voice options
- Context-aware conversations
- Multi-step speech interactions

### MCP App Store

The MCP App Store provides a centralized way to discover, install, and manage tools and capabilities for AgentRadis.

Features:
- Discover available tools and capabilities
- Install/uninstall tools on demand
- Categorize tools by functionality
- Search for specific capabilities

## Getting Started

### Installation

1. Clone the repository:
```bash
git clone https://github.com/scooter-lacroix/AgentRadis_v2.git
cd AgentRadis_v2
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the speech tool test:
```bash
python test_speech.py
```

### Using Speech Tools

The speech tools can be accessed through the Radis API or directly via the tool execution system:

```python
from app.app import Radis

async def main():
    radis = Radis()
    
    # Text-to-speech
    result = await radis.execute_tool("speech", 
        action="speak", 
        text="Hello, I am Radis!"
    )
    
    # Speech-to-text
    result = await radis.execute_tool("speech",
        action="listen",
        options={"timeout": 5.0}
    )
    
    if result["status"] == "success":
        print(f"You said: {result['text']}")
```

## MCP App Store Usage

The MCP App Store can be used to discover and install new capabilities:

```python
from app.app import Radis

async def main():
    radis = Radis()
    
    # Get available tools
    tools = await radis.get_available_tools()
    
    # Search for tools
    speech_tools = await radis.search_mcp_tools("speech")
    
    # Install a tool
    result = await radis.install_mcp_tool("realtimestt")
```
