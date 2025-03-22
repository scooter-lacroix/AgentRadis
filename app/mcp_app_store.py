"""
MCP App Store - Manager for Machine Capability Provider tools and apps
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

from app.logger import logger
from app.mcp_installer import MCPInstaller

class MCPAppStore:
    """
    MCP App Store for discovering and installing Machine Capability Provider tools
    
    The App Store manages a catalog of available MCP tools and capabilities,
    allowing Radis to discover and install new tools as needed.
    """
    
    # Default catalog file location
    DEFAULT_CATALOG_FILE = os.path.expanduser("~/.agentradis/mcp-catalog.json")
    
    # Catalog update interval (24 hours)
    UPDATE_INTERVAL = 86400
    
    def __init__(self, catalog_file: Optional[str] = None):
        """
        Initialize the MCP App Store.
        
        Args:
            catalog_file: Path to the catalog file (optional)
        """
        self.catalog_file = catalog_file or self.DEFAULT_CATALOG_FILE
        self.installer = MCPInstaller()
        self.catalog = self._load_catalog()
        
    def _load_catalog(self) -> Dict[str, Any]:
        """
        Load the MCP catalog from file or initialize with defaults.
        
        Returns:
            Dictionary containing the catalog
        """
        if os.path.exists(self.catalog_file):
            try:
                with open(self.catalog_file, "r") as f:
                    catalog = json.load(f)
                    logger.info(f"Loaded MCP catalog with {len(catalog.get('tools', []))} tools")
                    return catalog
            except json.JSONDecodeError:
                logger.error(f"Failed to parse MCP catalog file: {self.catalog_file}")
                return self._init_default_catalog()
            except Exception as e:
                logger.error(f"Error loading MCP catalog: {str(e)}")
                return self._init_default_catalog()
        else:
            return self._init_default_catalog()
            
    def _init_default_catalog(self) -> Dict[str, Any]:
        """
        Initialize the default catalog with built-in tools.
        
        Returns:
            Dictionary containing the default catalog
        """
        catalog = {
            "last_updated": int(time.time()),
            "tools": [
                {
                    "id": "realtimestt",
                    "name": "RealtimeSTT",
                    "description": "Real-time speech recognition library",
                    "version": "0.1.6",
                    "type": "library",
                    "category": "speech",
                    "tags": ["speech", "audio", "stt", "voice"],
                    "installation": {
                        "method": "pip",
                        "source": "pypi",
                        "package": "realtimestt==0.1.6"
                    },
                    "requirements": {
                        "os": ["windows", "linux", "macos"],
                        "dependencies": []
                    }
                },
                {
                    "id": "realtimetts",
                    "name": "RealtimeTTS",
                    "description": "Real-time text-to-speech library",
                    "version": "0.1.0",
                    "type": "library",
                    "category": "speech",
                    "tags": ["speech", "audio", "tts", "voice"],
                    "installation": {
                        "method": "pip",
                        "source": "pypi",
                        "package": "realtimetts==0.1.0"
                    },
                    "requirements": {
                        "os": ["windows", "linux", "macos"],
                        "dependencies": []
                    }
                },
                {
                    "id": "selenium",
                    "name": "Selenium",
                    "description": "Browser automation library",
                    "version": "4.9.0",
                    "type": "library",
                    "category": "browser",
                    "tags": ["web", "automation", "browser"],
                    "installation": {
                        "method": "pip",
                        "source": "pypi",
                        "package": "selenium==4.9.0"
                    },
                    "requirements": {
                        "os": ["windows", "linux", "macos"],
                        "dependencies": []
                    }
                },
                {
                    "id": "fsops",
                    "name": "File System Operations",
                    "description": "Enhanced file system operations",
                    "version": "1.0.0",
                    "type": "built-in",
                    "category": "filesystem",
                    "tags": ["files", "fs", "io"],
                    "installation": {
                        "method": "built-in",
                        "source": "internal"
                    },
                    "requirements": {
                        "os": ["windows", "linux", "macos"],
                        "dependencies": []
                    }
                },
                {
                    "id": "dbops",
                    "name": "Database Operations",
                    "description": "Database connection and query tools",
                    "version": "1.0.0",
                    "type": "built-in",
                    "category": "database",
                    "tags": ["database", "sql", "nosql", "query"],
                    "installation": {
                        "method": "built-in",
                        "source": "internal"
                    },
                    "requirements": {
                        "os": ["windows", "linux", "macos"],
                        "dependencies": []
                    }
                },
                {
                    "id": "netreq",
                    "name": "Network Requests",
                    "description": "Network request and API tools",
                    "version": "1.0.0",
                    "type": "built-in",
                    "category": "network",
                    "tags": ["network", "api", "http", "requests"],
                    "installation": {
                        "method": "built-in", 
                        "source": "internal"
                    },
                    "requirements": {
                        "os": ["windows", "linux", "macos"],
                        "dependencies": []
                    }
                }
            ]
        }
        
        # Save the default catalog
        self._save_catalog(catalog)
        logger.info(f"Initialized default MCP catalog with {len(catalog['tools'])} tools")
        
        return catalog
        
    def _save_catalog(self, catalog: Optional[Dict[str, Any]] = None):
        """
        Save the catalog to file.
        
        Args:
            catalog: Catalog to save (uses self.catalog if None)
        """
        catalog_to_save = catalog or self.catalog
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.catalog_file), exist_ok=True)
        
        with open(self.catalog_file, "w") as f:
            json.dump(catalog_to_save, f, indent=2)
            
    def update_catalog(self, force: bool = False) -> bool:
        """
        Update the catalog from remote sources.
        
        Args:
            force: Force update even if recently updated
            
        Returns:
            True if update successful, False otherwise
        """
        # Skip update if recently updated (within the last 24 hours)
        if not force:
            last_updated = self.catalog.get("last_updated", 0)
            current_time = int(time.time())
            
            if current_time - last_updated < self.UPDATE_INTERVAL:
                logger.info("Skipping MCP catalog update (recently updated)")
                return True
                
        # For now, just refresh from the local definition
        # In the future, this could pull from a remote source
        try:
            # Mark as updated
            self.catalog["last_updated"] = int(time.time())
            self._save_catalog()
            logger.info("Updated MCP catalog")
            return True
        except Exception as e:
            logger.error(f"Failed to update MCP catalog: {str(e)}")
            return False
            
    def get_available_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available tools, optionally filtered by category.
        
        Args:
            category: Category to filter by (optional)
            
        Returns:
            List of tool dictionaries
        """
        tools = self.catalog.get("tools", [])
        
        if category:
            return [tool for tool in tools if tool.get("category") == category]
        return tools
        
    def get_tool_by_id(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a tool by its ID.
        
        Args:
            tool_id: ID of the tool to retrieve
            
        Returns:
            Tool dictionary or None if not found
        """
        tools = self.catalog.get("tools", [])
        for tool in tools:
            if tool.get("id") == tool_id:
                return tool
        return None
        
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for tools by query.
        
        Args:
            query: Search query (matches name, description, tags)
            
        Returns:
            List of matching tool dictionaries
        """
        tools = self.catalog.get("tools", [])
        query = query.lower()
        
        # Simple search by name, description, and tags
        results = []
        for tool in tools:
            name = tool.get("name", "").lower()
            description = tool.get("description", "").lower()
            tags = [t.lower() for t in tool.get("tags", [])]
            
            if (query in name or 
                query in description or 
                any(query in tag for tag in tags)):
                results.append(tool)
                
        return results
        
    def is_installed(self, tool_id: str) -> bool:
        """
        Check if a tool is installed.
        
        Args:
            tool_id: ID of the tool to check
            
        Returns:
            True if installed, False otherwise
        """
        # Check if it's a built-in tool
        tool = self.get_tool_by_id(tool_id)
        if tool and tool.get("installation", {}).get("method") == "built-in":
            return True
            
        # Check if it's installed through the installer
        return self.installer.is_installed(tool_id)
        
    def install_tool(self, tool_id: str, force: bool = False) -> bool:
        """
        Install a tool by its ID.
        
        Args:
            tool_id: ID of the tool to install
            force: Force reinstallation if already installed
            
        Returns:
            True if installation successful, False otherwise
        """
        tool = self.get_tool_by_id(tool_id)
        if not tool:
            logger.error(f"Tool not found: {tool_id}")
            return False
            
        # Skip installation if it's built-in
        if tool.get("installation", {}).get("method") == "built-in":
            logger.info(f"Tool is built-in, no installation needed: {tool_id}")
            return True
            
        # Handle RealtimeSTT and RealtimeTTS specially
        if tool_id == "realtimestt":
            return self.installer.install_realtimestt(force)
        elif tool_id == "realtimetts":
            return self.installer.install_realtimetts(force)
            
        # Generic installation based on method
        installation = tool.get("installation", {})
        method = installation.get("method")
        
        if method == "pip":
            package = installation.get("package")
            if not package:
                logger.error(f"No package specified for pip installation: {tool_id}")
                return False
                
            try:
                import subprocess
                import sys
                
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Record the installation
                self.installer.config["installed"][tool_id] = {
                    "version": tool.get("version"),
                    "path": "python package",
                    "installed_at": "pip",
                    "description": tool.get("description"),
                }
                self.installer._save_config()
                
                logger.info(f"Successfully installed {tool_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to install {tool_id}: {str(e)}")
                return False
        else:
            logger.error(f"Unsupported installation method: {method}")
            return False
            
    def uninstall_tool(self, tool_id: str) -> bool:
        """
        Uninstall a tool by its ID.
        
        Args:
            tool_id: ID of the tool to uninstall
            
        Returns:
            True if uninstallation successful, False otherwise
        """
        tool = self.get_tool_by_id(tool_id)
        if not tool:
            logger.error(f"Tool not found: {tool_id}")
            return False
            
        # Cannot uninstall built-in tools
        if tool.get("installation", {}).get("method") == "built-in":
            logger.error(f"Cannot uninstall built-in tool: {tool_id}")
            return False
            
        # Use the installer to uninstall
        return self.installer.uninstall(tool_id)
        
    def get_tool_info(self, tool_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a tool.
        
        Args:
            tool_id: ID of the tool to get info for
            
        Returns:
            Dictionary with tool information and installation status
        """
        tool = self.get_tool_by_id(tool_id)
        if not tool:
            return {"error": f"Tool not found: {tool_id}"}
            
        # Add installation status
        tool_info = dict(tool)
        tool_info["installed"] = self.is_installed(tool_id)
        
        # Add installation details if installed
        if tool_info["installed"] and tool_id in self.installer.config["installed"]:
            tool_info["installation_details"] = self.installer.config["installed"][tool_id]
            
        return tool_info
        
    def get_categories(self) -> List[str]:
        """
        Get all available categories.
        
        Returns:
            List of category names
        """
        tools = self.catalog.get("tools", [])
        categories = set()
        
        for tool in tools:
            category = tool.get("category")
            if category:
                categories.add(category)
                
        return sorted(list(categories))
        
    def get_tools_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all tools organized by category.
        
        Returns:
            Dictionary mapping category names to lists of tools
        """
        categories = self.get_categories()
        result = {}
        
        for category in categories:
            result[category] = self.get_available_tools(category)
            
        return result 