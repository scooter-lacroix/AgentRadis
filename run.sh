#!/bin/bash

# AgentRadis Run Script
# This script helps run AgentRadis in different modes

# Display help message
show_help() {
    echo "AgentRadis Run Script"
    echo "-------------------"
    echo "Usage: ./run.sh [option] [prompt]"
    echo ""
    echo "Options:"
    echo "  --web          Start with web interface"
    echo "  --api          Start API server only"
    echo "  --flow         Use Flow execution mode"
    echo "  --config       Show current configuration"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run.sh --web                  # Start web interface"
    echo "  ./run.sh --flow \"create a file\" # Run flow with prompt"
    echo "  ./run.sh \"search for cats\"      # Run with prompt"
    echo "  ./run.sh --config              # Show current configuration"
    echo ""
}

# Handle help argument
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if a virtual environment exists, if not create one
if [ ! -d "open_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv open_env
    source open_env/bin/activate
    pip install -e .
else
    source open_env/bin/activate
fi

# Handle specific modes first
if [ "$1" == "--web" ]; then
    echo "Starting AgentRadis Web Interface..."
    python -m main --web
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        # Check for specific error messages in the output
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Make sure app/tool/planning.py is properly imported and initialized."
            echo "Trying to fix by updating Python path..."
            export PYTHONPATH=$PYTHONPATH:$(pwd)
            python -m main --web
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. This usually indicates a missing initialization or null value."
            echo "Attempting fix with debug mode..."
            python -m main --web --debug
            EXIT_CODE=$?
        fi
    fi
    exit $EXIT_CODE
elif [ "$1" == "--api" ]; then
    echo "Starting AgentRadis API Server..."
    python -m main --api
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Make sure app/tool/planning.py is properly imported and initialized."
            echo "Trying to fix by updating Python path..."
            export PYTHONPATH=$PYTHONPATH:$(pwd)
            python -m main --api
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. This usually indicates a missing initialization or null value."
            echo "Attempting fix with debug mode..."
            python -m main --api --debug
            EXIT_CODE=$?
        fi
    fi
    exit $EXIT_CODE
elif [ "$1" == "--config" ]; then
    echo "Showing AgentRadis Configuration..."
    python -m main --config
    exit $?
# Handle regular flow and other options
elif [[ "${1}" == --* ]] || [[ "${1}" == -* ]]; then
    echo "Running AgentRadis Flow with options: $@"
    python -m main "$@" 2>error.log
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Trying to fix..."
            export PYTHONPATH=$PYTHONPATH:$(pwd)
            python -m run_flow.py "$@"
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. Attempting fix with debug mode..."
            python -m main --debug "$@"
            EXIT_CODE=$?
        fi
    fi
# If no arguments are provided, run in interactive mode
elif [ $# -eq 0 ]; then
    echo "Running AgentRadis in interactive mode"
    python -m main 2>error.log
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Trying to run in flow mode instead..."
            python -m run_flow.py
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. Attempting fix with debug mode..."
            python -m main --debug
            EXIT_CODE=$?
        fi
    fi
# Otherwise, treat the first argument as a prompt for flow mode
else
    echo "Running AgentRadis with prompt: $1"
    python -m main "$@" 2>error.log
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Trying flow mode instead..."
            python -m run_flow.py "$@"
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. Attempting fix with debug mode..."
            python -m main --debug "$@"
            EXIT_CODE=$?
        fi
    fi
fi

# Check exit status
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "Error: Command exited with status $EXIT_CODE"
    # Check if this is a known error type
    if [ -f error.log ] && grep -q "Input should be an instance of PlanningTool" error.log; then
        echo "This appears to be a PlanningTool initialization issue."
        echo "Try running: 'python -m run_flow.py' instead of main.py."
    elif [ -f error.log ] && grep -q "'NoneType' object is not iterable" error.log; then
        echo "This appears to be a null value issue, which often occurs with uninitialized objects."
        echo "Try running with debug flag: 'python -m main --debug'"
    fi
    exit $EXIT_CODE
fi

# Clean up error log if everything succeeded
if [ -f error.log ]; then
    rm error.log
fi