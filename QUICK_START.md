# OpenManus Quick Start Guide

OpenManus is a versatile AI agent system with powerful tools for file saving, web searching, code execution, and more. This quick start guide will help you get up and running.

## Prerequisites

- Python 3.9 or newer
- pip package manager

## Installation

1. Clone the repository (if you haven't already):
   ```
   git clone https://github.com/yourusername/OpenManus.git
   cd OpenManus
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install browser dependencies (for browser tools):
   ```
   playwright install
   ```

## Running OpenManus

### Shell Script (Recommended)

The easiest way to start OpenManus is by using the shell script:

```bash
# Make the script executable (first time only)
chmod +x run.sh

# Start with web interface
./run.sh --web

# Start API server only
./run.sh --api

# Use flow mode with a prompt
./run.sh --flow "your prompt here"

# Process a prompt directly
./run.sh "your prompt here"

# Get help
./run.sh --help
```

### Python Startup Script

You can also use the Python startup script:

```bash
# Make the script executable (first time only)
chmod +x start_openmanus.py

# Start with web interface
./start_openmanus.py --web

# Start API server only
./start_openmanus.py --api

# Use flow mode with web interface
./start_openmanus.py --flow --web

# Process a prompt directly
./start_openmanus.py "your prompt here"
```

### Other Methods

You can also choose any of the following methods:

#### 1. Web Interface

Start the API server and access the web interface:

```
python api.py
```

Or:

```
python main.py --web
```

Then open your browser and go to:
- http://localhost:5000/ui/openmanus_interface.html

In the web interface:
1. Connect to `http://localhost:5000`
2. Type your prompt in the input box
3. Click "Send" to process your request

#### 2. Command Line Interface

Use the command line interface:

```
python main.py
```

This will start an interactive session where you can enter prompts.

Or specify a prompt directly:

```
python main.py "your prompt here"
```

#### 3. API Usage

If you're developing an application that needs to use OpenManus:

1. Start the API server:
   ```
   python api.py
   ```

2. Send requests to the API:
   ```
   curl -X POST "http://localhost:5000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Your prompt here"}'
   ```

## Available Tools

OpenManus includes several powerful tools:

- **file_saver**: Save content to files on your system
- **web_search**: Search the web for information
- **python_execute**: Execute Python code
- **browser_use**: Navigate and extract data from websites
- **terminate**: End the current task

## Troubleshooting

If you encounter any issues:

1. Check that all dependencies are installed correctly
2. Make sure no other service is using port 5000
3. Check the console for error messages
4. Restart the application if it becomes unresponsive

## Feedback and Support

If you encounter any problems or have suggestions for improvements, please open an issue on our GitHub repository.

Happy using OpenManus! 