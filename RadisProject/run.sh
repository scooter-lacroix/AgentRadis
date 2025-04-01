#!/usr/bin/env bash

# Ensure UTF-8 encoding
export LANG=en_US.UTF-8
# Set up colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Formatting functions
print_separator() {
    echo -e "\n${BLUE}=====================================${NC}"
    echo -e "${BLUE}           $1${NC}"
    echo -e "${BLUE}=====================================${NC}\n"
}

print_progress() {
    echo -e "${GREEN}$1${NC}"
}

print_tool_usage() {
    echo -e "${CYAN}Using $1 to $2${NC}"
}

print_thinking() {
    echo -e "${YELLOW}Thinking: $1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_processing() {
    local messages=("Just a moment while I process that..." "Processing your request, this will take a few seconds..." "Working on it, almost there..." "Analyzing your request, just a few more seconds..." "I'm composing a thorough response for you...")
    local rand=$((RANDOM % ${#messages[@]}))
    print_progress "${messages[$rand]}"
}

# Function to display help
show_help() {
    # ASCII art for AgentRadis
    echo -e "${BLUE}"
    echo "    _                     _   ____            _ _     "
    echo "   / \   __ _  ___ _ __ | |_|  _ \ __ _  __| (_)___ "
    echo "  / _ \ / _\` |/ _ \ '_ \| __| |_) / _\` |/ _\` | / __|"
    echo " / ___ \ (_| |  __/ | | | |_|  _ < (_| | (_| | \__ \\"
    echo "/_/   \_\__, |\___|_| |_|\__|_| \_\__,_|\__,_|_|___/"
    echo "        |___/                                         "
    echo -e "${NC}"

    # Title and separator
    echo -e "${YELLOW}✧ Command Line Interface ✧${NC}"
    echo -e "${BLUE}════════════════════════════════════════════${NC}"
    echo ""

    # Usage section with improved formatting
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./run.sh [option] [prompt]"
    echo ""

    # Options section with star bullets and aligned descriptions
    echo -e "${GREEN}Options:${NC}"
    echo -e "  ${YELLOW}✦${NC} --web          Start with web interface"
    echo -e "  ${YELLOW}✦${NC} --api          Start API server only"
    echo -e "  ${YELLOW}✦${NC} --flow         Use Flow execution mode"
    echo -e "  ${YELLOW}✦${NC} --config       Show current configuration"
    echo -e "  ${YELLOW}✦${NC} -h, --help     Show this help message"
    echo ""
    # Try parsing different JSON formats
    # First, try nested JSON with content field
    if echo "$raw_response" | grep -q '"content"[:]\\s*{'; then
        cleaned=$(echo "$raw_response" | grep -o '"content"[:]\\s*{\\s*"[^"]*"[:]\\s*"[^"]*"' | sed -E 's/"content"[:]\\s*{\\s*"[^"]*"[:]\\s*"([^"]*)"/\\1/')
    fi
    echo ""
    echo -e "  ${BLUE}▶${NC} ./run.sh --flow \"create a file\""
    echo "     Run flow mode with a specific prompt"
    echo ""
    echo -e "  ${BLUE}▶${NC} ./run.sh \"search for cats\""
    echo "     Execute a direct search prompt"
    echo ""
    echo -e "  ${BLUE}▶${NC} ./run.sh --config"
    echo "     Display current configuration"
    echo ""

    # Footer
    echo -e "${BLUE}════════════════════════════════════════════${NC}"
}

# Function to clean and extract the actual response content
clean_response() {
    local raw_response="$1"
    local cleaned=""
    
    # Handle Message object format first
    if echo "$raw_response" | grep -q "Message object"; then
        # Extract content from Message object format
        cleaned=$(echo "$raw_response" | grep -o "'content': '[^']*'" | sed "s/'content': '\(.*\)'/\1/")
        if [ ! -z "$cleaned" ]; then
            echo "$cleaned"
            return
        fi
    fi
    
    # Try parsing different JSON formats
    # First, try nested JSON with content field
    if echo "$raw_response" | grep -q '"content"[:]\s*{'; then
        cleaned=$(echo "$raw_response" | grep -o '"content"[:]\s*{\s*"[^"]*"[:]\s*"[^"]*"' | sed -E 's/"content"[:]\s*{\s*"[^"]*"[:]\s*"([^"]*)"/\1/')
    fi
    
    # Try standard JSON fields
    if [ -z "$cleaned" ]; then
        for field in "response" "answer" "message" "content"; do
            if echo "$raw_response" | grep -q "\"$field\"[:]\s*\""; then
                cleaned=$(echo "$raw_response" | grep -o "\"$field\"[:]\s*\"[^\"]*\"" | sed -E "s/\"$field\"[:]\s*\"([^\"]*)\"/\1/")
                break
            fi
        done
    fi
    
    # Try single-quoted fields if double-quoted parsing failed
    if [ -z "$cleaned" ]; then
        for field in "response" "answer" "message" "content"; do
            if echo "$raw_response" | grep -q "'$field'[:]\s*'"; then
                cleaned=$(echo "$raw_response" | grep -o "'$field'[:]\s*'[^']*'" | sed -E "s/'$field'[:]\s*'([^']*)'/\1/")
                break
            fi
        done
    fi
    
    # Handle escaped characters
    if [ ! -z "$cleaned" ]; then
        # Unescape newlines and quotes
        cleaned=$(echo "$cleaned" | sed 's/\\n/\n/g' | sed 's/\\"/"/g' | sed "s/\\'/'/g")
        echo "$cleaned"
    else
        # If no JSON formatting found or parsing failed, return the original response
        # Remove any obvious error markers
        echo "$raw_response" | sed 's/^Error:\s*//' | sed 's/^Warning:\s*//'
    fi
}

# Function to display formatted responses
display_response() {
    local response="$1"
    local sender="Radis"
    
    # Clean the response first
    local cleaned_response=$(clean_response "$response")
    
    # Remove any existing "Radis:" prefix to avoid duplication
    cleaned_response=$(echo "$cleaned_response" | sed 's/^Radis:\s*//')
    
    # Format the final response
    local formatted_response="$sender: $cleaned_response"
    
    # Define colors and box properties
    local outer_border_color="\033[1;34m"  # Blue color for outer border
    local inner_border_color="\033[1;36m"  # Cyan color for inner border
    local text_color="\033[0;37m"          # White color for text
    local title_color="\033[1;37m"         # Bright white for title
    local reset_color="\033[0m"
    
    # Box dimensions
    local box_width=100
    local content_width=$((box_width - 4))  # Account for borders and padding
    
    # Simple box drawing characters that are UTF-8 compatible
    local h_outer="-"  # Horizontal outer
    local v_outer="|"  # Vertical outer
    local tl_outer="+" # Top-left outer
    local tr_outer="+" # Top-right outer
    local bl_outer="+" # Bottom-left outer
    local br_outer="+" # Bottom-right outer
    
    local h_inner="-"  # Horizontal inner
    local v_inner="|"  # Vertical inner
    local tl_inner="+" # Top-left inner
    local tr_inner="+" # Top-right inner
    local bl_inner="+" # Bottom-left inner
    local br_inner="+" # Bottom-right inner
    
    # Create title box
    # Calculate padding to center the title, accounting for title length
    local title="RESULT"
    local title_length=${#title}
    local title_padding=$(( (box_width - title_length) / 2 ))
    local title_line=$(printf "%${title_padding}s%s%${title_padding}s" "" "$title" "")
    # If box_width minus padding and title length is odd, add an extra space
    if [ $(( box_width - (2 * title_padding) - title_length )) -eq 1 ]; then
        title_line="$title_line "
    fi
    
    # Print outer box with title
    echo -e "\n${outer_border_color}$tl_outer$(printf '%*s' $box_width | tr ' ' "$h_outer")$tr_outer${reset_color}"
    echo -e "${outer_border_color}$v_outer${inner_border_color}$tl_inner$(printf '%*s' $((box_width-2)) | tr ' ' "$h_inner")$tr_inner${outer_border_color}$v_outer${reset_color}"
    echo -e "${outer_border_color}$v_outer${inner_border_color}$v_inner${title_color}$title_line${inner_border_color}$v_inner${outer_border_color}$v_outer${reset_color}"
    echo -e "${outer_border_color}$v_outer${inner_border_color}$bl_inner$(printf '%*s' $((box_width-2)) | tr ' ' "$h_inner")$br_inner${outer_border_color}$v_outer${reset_color}"
    
    # Content section
    echo -e "${outer_border_color}$tl_outer$(printf '%*s' $box_width | tr ' ' "$h_outer")$tr_outer${reset_color}"
    
    # Word wrap and display the message with proper padding
    # Use process substitution to avoid subshell issues
    while IFS= read -r line; do
        # Trim line to content width if it's too long
        line="${line:0:$content_width}"
        # Calculate actual line width (considering UTF-8 characters)
        local line_width=$(echo -n "$line" | wc -m)
        # Calculate padding needed
        local padding=$((content_width - line_width))
        # Print the line with proper padding
        printf "${outer_border_color}$v_outer${text_color}  %s%-${padding}s  ${outer_border_color}$v_outer${reset_color}\n" "$line" ""
    done < <(echo "$formatted_response" | fold -s -w $content_width)
    
    # Bottom border
    echo -e "${outer_border_color}$bl_outer$(printf '%*s' $box_width | tr ' ' "$h_outer")$br_outer${reset_color}\n"
}
# Main execution logic
main() {
    local prompt="$1"
    local debug_flag="$2"
    
    print_separator "Starting AgentRadis"
    print_processing
    
    # Run the Python module with the prompt, capturing both stdout and stderr
    if [ "$debug_flag" == "--debug" ]; then
        local result=$(python -m run_flow "$prompt" --debug 2>error.log | while IFS= read -r line; do
            if [[ $line == *"INFO"* ]]; then
                if [[ $line == *"Using tool"* ]]; then
                    tool_name=$(echo "$line" | sed -n 's/.*Using tool \([^:]*\):.*/\1/p')
                    tool_action=$(echo "$line" | sed 's/.*INFO[^:]*: //')
                    print_tool_usage "$tool_name" "$tool_action"
                elif [[ $line == *"Thinking"* ]]; then
                    thought=$(echo "$line" | sed 's/.*INFO[^:]*: //')
                    print_thinking "$thought"
                fi
            elif [[ $line == *"ERROR"* ]]; then
                print_error "$(echo "$line" | sed 's/.*ERROR: //')"
            else
                echo "$line"
            fi
        done)
    else
        local result=$(python -m run_flow "$prompt" 2>error.log | while IFS= read -r line; do
            if [[ $line == *"INFO"* ]]; then
                if [[ $line == *"Using tool"* ]]; then
                    tool_name=$(echo "$line" | sed -n 's/.*Using tool \([^:]*\):.*/\1/p')
                    tool_action=$(echo "$line" | sed 's/.*INFO[^:]*: //')
                    print_tool_usage "$tool_name" "$tool_action"
                elif [[ $line == *"Thinking"* ]]; then
                    thought=$(echo "$line" | sed 's/.*INFO[^:]*: //')
                    print_thinking "$thought"
                fi
            elif [[ $line == *"ERROR"* ]]; then
                print_error "$(echo "$line" | sed 's/.*ERROR: //')"
            else
                echo "$line"
            fi
        done)
    fi
    
    # Extract the processed_response from the result
    # Try to extract processed_response in multiple formats
    local processed_response=""
    
    # Try JSON format first
    if echo "$result" | grep -q '"processed_response":\s*"'; then
        processed_response=$(echo "$result" | grep -o '"processed_response":\s*"[^"]*"' | head -1 | sed 's/"processed_response":\s*"\(.*\)"/\1/')
    elif echo "$result" | grep -q '"response":\s*"'; then
        processed_response=$(echo "$result" | grep -o '"response":\s*"[^"]*"' | head -1 | sed 's/"response":\s*"\(.*\)"/\1/')
    elif echo "$result" | grep -q '"message":\s*"'; then
        processed_response=$(echo "$result" | grep -o '"message":\s*"[^"]*"' | head -1 | sed 's/"message":\s*"\(.*\)"/\1/')
    fi
    
    # If we couldn't extract a response, show the full output
    if [ -z "$processed_response" ]; then
        processed_response="$result"
    fi
    
    # Display the response
    display_response "$processed_response"
}

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
    echo "Ensuring dependencies are installed..."
    pip install -q -r requirements.txt
fi

# Check if help is requested
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

# Handle specific modes first
if [ "$1" == "--web" ]; then
    echo "Starting AgentRadis Web Interface..."
    # Check if debug mode is specified
    if [ "$2" == "--debug" ]; then
        echo "Running in debug mode..."
        python -m main --web --debug 2>error.log
    else
        python -m main --web 2>error.log
    fi
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        # Check for specific error messages in the output
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Make sure app/tool/planning.py is properly imported and initialized."
            echo "Trying to fix by updating Python path..."
            export PYTHONPATH=$PYTHONPATH:$(pwd)
            if [ "$2" == "--debug" ]; then
                python -m main --web --debug 2>error.log
            else
                python -m main --web 2>error.log
            fi
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. This usually indicates a missing initialization or null value."
            echo "Attempting fix with debug mode..."
            python -m main --web --debug 2>error.log
            EXIT_CODE=$?
        fi
    fi
    exit $EXIT_CODE
elif [ "$1" == "--api" ]; then
    echo "Starting AgentRadis API Server..."
    # Check if debug mode is specified
    if [ "$2" == "--debug" ]; then
        echo "Running in debug mode..."
        python -m main --api --debug 2>error.log
    else
        python -m main --api 2>error.log
    fi
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Make sure app/tool/planning.py is properly imported and initialized."
            echo "Trying to fix by updating Python path..."
            export PYTHONPATH=$PYTHONPATH:$(pwd)
            if [ "$2" == "--debug" ]; then
                python -m main --api --debug 2>error.log
            else
                python -m main --api 2>error.log
            fi
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. This usually indicates a missing initialization or null value."
            echo "Attempting fix with debug mode..."
            python -m main --api --debug 2>error.log
            EXIT_CODE=$?
        fi
    fi
    exit $EXIT_CODE
elif [ "$1" == "--config" ]; then
    echo "Showing AgentRadis Configuration..."
    python -c "from app.config import config; print(config.model_dump_json(indent=2))" 2>error.log
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo "Error showing configuration: "
        cat error.log
    fi
    exit $EXIT_CODE
# Handle regular flow and other options
elif [[ "${1}" == --* ]] || [[ "${1}" == -* ]]; then
    print_separator "Starting AgentRadis Flow"
    print_processing
    # Check for debug flag
    if [[ "$*" == *"--debug"* ]]; then
        DEBUG_FLAG="--debug"
        # Remove debug flag from arguments to pass to flow
        ARGS=$(echo "$@" | sed 's/--debug//')
    else
        DEBUG_FLAG=""
        ARGS="$@"
    fi
    
    OUTPUT=$(python -m run_flow $ARGS 2>error.log)
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Trying to fix..."
            export PYTHONPATH=$PYTHONPATH:$(pwd)
            OUTPUT=$(python -m run_flow $ARGS 2>error.log)
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. Attempting fix with debug mode..."
            OUTPUT=$(python -m run_flow $ARGS --debug 2>error.log)
            EXIT_CODE=$?
        elif grep -q "plan_" error.log 2>/dev/null; then
            echo "Error with plan ID handling. Trying to fix..."
            # Try to run with a specified plan ID
            PLAN_ID="plan_$(date +%s)"
            OUTPUT=$(python -m run_flow $ARGS --plan-id=$PLAN_ID 2>error.log)
            EXIT_CODE=$?
        fi
    fi
    # Display formatted response
    if echo "$OUTPUT" | grep -q "processed_response"; then
        # Extract the processed_response field
        processed_response=$(echo "$OUTPUT" | grep -o '"processed_response": "[^"]*"' | sed 's/"processed_response": "\(.*\)"/\1/')
        
        # Display the processed response
        display_response "$processed_response"
    else
        # Display the raw response
        display_response "$OUTPUT"
    fi
# If no arguments are provided, run in interactive mode
elif [ $# -eq 0 ]; then
    print_separator "Starting AgentRadis Interactive Mode"
    print_processing
    python -m main 2>error.log
    EXIT_CODE=$?
    # Handle specific errors
    if [ $EXIT_CODE -ne 0 ]; then
        if grep -q "Input should be an instance of PlanningTool" error.log 2>/dev/null; then
            echo "Error: PlanningTool validation failed. Trying to run in flow mode instead..."
            python -m run_flow 2>error.log
            EXIT_CODE=$?
        elif grep -q "'NoneType' object is not iterable" error.log 2>/dev/null; then
            echo "Error: NoneType object is not iterable. Attempting fix with debug mode..."
            python -m main --debug 2>error.log
            EXIT_CODE=$?
        elif grep -q "plan_" error.log 2>/dev/null; then
            echo "Error with plan ID handling. Attempting to fix..."
            # Try to run with a specified plan ID
            PLAN_ID="plan_$(date +%s)"
            python -m main --plan-id=$PLAN_ID --debug 2>error.log
            EXIT_CODE=$?
        fi
    fi
# Otherwise, treat the first argument as a prompt for flow mode
else
    # Check for debug flag in all arguments
    if [[ " $* " =~ " --debug " ]]; then
        DEBUG_FLAG="--debug"
        # Remove debug flag from arguments
        ARGS=$(echo "$@" | sed 's/--debug//')
    else
        DEBUG_FLAG=""
        ARGS="$@"
    fi
    main "$ARGS" "$DEBUG_FLAG"
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