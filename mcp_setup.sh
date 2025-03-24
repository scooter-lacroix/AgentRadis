#!/bin/bash
# Setup script for MCP server support in AgentRadis

echo "Setting up MCP server support for AgentRadis..."

# Check for npm
if ! command -v npm &> /dev/null; then
    echo "Error: npm is required but not installed. Please install Node.js and npm first."
    exit 1
fi

# Check for npx
if ! command -v npx &> /dev/null; then
    echo "Error: npx is required but not installed. Please install Node.js and npm first."
    exit 1
fi

# Install mcp-installer
echo "Installing @anaisbetts/mcp-installer..."
npm install -g @anaisbetts/mcp-installer

# Check for uv (Python installer)
if ! command -v uv &> /dev/null; then
    echo "Warning: 'uv' is not installed. This is required for Python-based MCP servers."
    echo "Would you like to install uv? (y/n)"
    read install_uv
    
    if [[ $install_uv == "y" || $install_uv == "Y" ]]; then
        echo "Installing uv..."
        curl -fsSL https://github.com/astral-sh/uv/releases/download/0.1.22/uv-installer.sh | sh
    else
        echo "Skipping uv installation. Note that Python-based MCP servers will not work."
    fi
fi

# Create MCP servers directory
mkdir -p ~/.agentradis/mcp-servers

echo "MCP setup complete!"
echo "You can now use the mcp_installer tool to install and manage MCP servers."
echo "Example usage in AgentRadis: Install the MCP server named @modelcontextprotocol/server-filesystem" 