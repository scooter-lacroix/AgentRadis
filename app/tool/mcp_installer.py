import asyncio
import json
import os
import re
import subprocess
import shutil
import time
from typing import Any, Dict, List, Optional, Set, Type, Union

from app.logger import logger, get_tool_logger
from app.tool.tool import Tool
from app.schema import ToolResult
from app.config import config
from app.exceptions import ToolExecutionException

class MCPInstaller(Tool):
    """Tool to install and manage MCP servers."""
    
    name = "mcp_installer"
    description = "Install and manage Model Context Protocol (MCP) servers. MCP is a protocol that standardizes how applications provide context to LLMs."
    examples = [
        "Install the MCP server named mcp-server-fetch",
        "Install the @modelcontextprotocol/server-filesystem package as an MCP server",
        "Install the MCP server from a local directory path",
        "Set environment variables for an MCP server"
    ]
    is_stateful = True
    timeout = 300.0  # Default timeout increased to 5 minutes
    parameters = {
        "type": "object",
        "properties": {
            "server_name": {
                "type": "string",
                "description": "Name of the MCP server to install or manage"
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional arguments for server installation"
            },
            "env_vars": {
                "type": "object",
                "description": "Environment variables for the server",
                "additionalProperties": {"type": "string"}
            },
            "local_path": {
                "type": "string",
                "description": "Local path for installing from a directory"
            }
        },
        "required": ["server_name"]
    }
    
    # Package-specific timeouts (in seconds) for known large packages
    PACKAGE_TIMEOUTS = {
        "puppeteer-mcp-server": 600,  # 10 minutes for Puppeteer
        "playwright-mcp-server": 600,  # 10 minutes for Playwright
        "@modelcontextprotocol/server-browser": 480,  # 8 minutes for browser server
        "browser-automation": 480,  # 8 minutes for browser automation
    }
    
    # Background installation tracking
    background_installs = {}
    
    # Track installed servers
    installed_servers = {}
    server_processes = {}
    
    def __init__(self):
        """Initialize the MCP installer tool."""
        super().__init__()
        self.logger = get_tool_logger(self.name)
        self.servers_dir = os.path.join(os.path.expanduser("~"), ".agentradis", "mcp-servers")
        
        # Create servers directory if it doesn't exist
        os.makedirs(self.servers_dir, exist_ok=True)
        
        # Load previously installed servers if any
        self._load_installed_servers()
        
        # Reference to the agent that owns this tool (will be set later)
        self.agent = None
    
    def _load_installed_servers(self):
        """Load previously installed servers from disk."""
        servers_config_path = os.path.join(self.servers_dir, "servers.json")
        if os.path.exists(servers_config_path):
            try:
                with open(servers_config_path, 'r') as f:
                    self.installed_servers = json.load(f)
                    self.logger.info(f"Loaded {len(self.installed_servers)} previously installed MCP servers")
            except Exception as e:
                self.logger.error(f"Failed to load installed servers: {e}")
                self.installed_servers = {}
    
    def _save_installed_servers(self):
        """Save installed servers to disk."""
        servers_config_path = os.path.join(self.servers_dir, "servers.json")
        try:
            with open(servers_config_path, 'w') as f:
                json.dump(self.installed_servers, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save installed servers: {e}")
    
    def _get_dynamic_timeout(self, server_name: str) -> float:
        """
        Get a dynamic timeout based on the server package.
        
        Args:
            server_name: Name of the server package
            
        Returns:
            Timeout value in seconds
        """
        # Check for exact matches in package timeouts
        if server_name in self.PACKAGE_TIMEOUTS:
            return self.PACKAGE_TIMEOUTS[server_name]
        
        # Check for partial matches (e.g., if server_name contains keywords)
        for pkg, timeout in self.PACKAGE_TIMEOUTS.items():
            if pkg in server_name or server_name in pkg:
                return timeout
                
        # For browser-related packages, provide a longer timeout
        if any(term in server_name.lower() for term in ["browser", "puppeteer", "playwright", "chrome", "firefox"]):
            return 600.0  # 10 minutes for browser-related packages
            
        # Default timeout for unknown packages (5 minutes)
        return 300.0

    async def _execute(self, 
                     server_name: str, 
                     args: Optional[List[str]] = None, 
                     env_vars: Optional[Dict[str, str]] = None,
                     local_path: Optional[str] = None,
                     force_timeout: Optional[float] = None) -> ToolResult:
        """
        Install and configure an MCP server.
        
        Args:
            server_name: Name of the MCP server to install
            args: Optional list of arguments to pass to the server
            env_vars: Optional dictionary of environment variables for the server
            local_path: Optional local path to the server (if not installing from npm/PyPI)
            force_timeout: Optional timeout override (in seconds)
            
        Returns:
            ToolResult with information about the installed server
        """
        # Validate server name
        if not server_name:
            raise ToolExecutionException("Server name is required")
        
        # Check if this is a background installation that's already in progress
        if server_name in self.background_installs:
            return await self._check_background_installation(server_name)
        
        # Set dynamic timeout if not forced
        dynamic_timeout = force_timeout or self._get_dynamic_timeout(server_name)
        
        # Default args and env_vars if not provided
        args = args or []
        env_vars = env_vars or {}
        
        # Determine if this is an npm package, PyPI package, or local path
        is_npm = server_name.startswith('@') or re.match(r'^[a-zA-Z0-9-]+$', server_name)
        is_path = os.path.exists(local_path) if local_path else os.path.exists(server_name)
        
        # Set unique server ID
        server_id = server_name.replace('/', '_').replace('@', '').replace('\\', '_')
        if server_id in self.installed_servers:
            self.logger.info(f"Server {server_id} already installed, updating configuration")
        else:
            self.logger.info(f"Installing MCP server: {server_name} (ID: {server_id}) with timeout {dynamic_timeout}s")
        
        # Set up the installation
        try:
            # Start a timer for progress reporting
            start_time = time.time()
            
            # Set installation method based on package type
            install_method = None
            if is_path or local_path:
                install_method = self._install_from_path
                source_path = local_path or server_name
                self.logger.info(f"Installing from local path: {source_path}")
            elif is_npm:
                install_method = self._install_from_npm
                self.logger.info(f"Installing from npm: {server_name}")
            else:
                install_method = self._install_from_pypi
                self.logger.info(f"Installing from PyPI: {server_name}")
            
            # Create a task for the installation with the dynamic timeout
            installation_task = asyncio.create_task(
                install_method(server_id, server_name if not is_path else source_path, args, env_vars)
            )
            
            # Wait for the installation to complete with progress reporting
            server_info = None
            try:
                progress_task = asyncio.create_task(self._report_progress(server_name, start_time))
                
                # Wait for installation to complete with timeout
                try:
                    server_info = await asyncio.wait_for(installation_task, timeout=dynamic_timeout)
                    await progress_task  # Ensure progress task is cancelled
                except asyncio.TimeoutError:
                    # If timeout occurs, log but don't cancel the task - move to background
                    elapsed_time = time.time() - start_time
                    self.logger.warning(f"Installation timed out after {elapsed_time:.1f}s, moving to background")
                    
                    # Track the background installation
                    self.background_installs[server_name] = {
                        "task": installation_task,
                        "start_time": start_time,
                        "server_id": server_id,
                        "args": args,
                        "env_vars": env_vars
                    }
                    
                    # Return partial result with background status
                    return ToolResult(
                        tool=self.name,
                        action="install_mcp_server",
                        status="PENDING",
                        result={
                            "server_id": server_id,
                            "server_name": server_name,
                            "message": f"Installation of {server_name} is still in progress in the background",
                            "note": "The installation is taking longer than expected. You can check its status later by calling the mcp_installer tool again with the same server name.",
                            "elapsed_time": f"{elapsed_time:.1f} seconds",
                            "background": True
                        }
                    )
            finally:
                # Cancel progress reporting if still active
                if 'progress_task' in locals() and not progress_task.done():
                    progress_task.cancel()
            
            # If we got here, installation was successful
            if server_info:
                # Store server information
                self.installed_servers[server_id] = server_info
                self._save_installed_servers()
                
                # Register the server with the agent if available
                registered = False
                if hasattr(self, 'agent') and self.agent is not None and hasattr(self.agent, 'register_mcp_server'):
                    try:
                        registered = await self.agent.register_mcp_server(server_info)
                        if registered:
                            self.logger.info(f"Registered server {server_id} with agent for immediate use")
                    except Exception as e:
                        self.logger.error(f"Failed to register server with agent: {e}")
                
                # Installation successful
                elapsed_time = time.time() - start_time
                return ToolResult(
                    tool=self.name,
                    action="install_mcp_server",
                    status="SUCCESS",
                    result={
                        "server_id": server_id,
                        "server_name": server_name,
                        "server_info": server_info,
                        "message": f"Successfully installed MCP server: {server_name}",
                        "note": f"The server is now available as a tool with the name: {server_info['tool_name']}",
                        "registered_for_immediate_use": registered,
                        "installation_time": f"{elapsed_time:.1f} seconds"
                    }
                )
            
        except Exception as e:
            self.logger.error(f"Failed to install MCP server {server_name}: {e}")
            return ToolResult(
                tool=self.name,
                action="install_mcp_server",
                status="ERROR",
                result={
                    "error": f"Failed to install MCP server: {e}",
                    "suggestion": "Make sure the server name is correct and the required tools (npx/uv) are installed."
                }
            )
    
    async def _report_progress(self, server_name: str, start_time: float, interval: float = 15.0):
        """
        Report progress periodically during installation.
        
        Args:
            server_name: Name of the server being installed
            start_time: When installation started
            interval: How often to report progress (in seconds)
        """
        try:
            while True:
                elapsed = time.time() - start_time
                self.logger.info(f"Installation of {server_name} in progress ({elapsed:.1f}s elapsed)")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            # Task was cancelled, which is expected
            pass
    
    async def _check_background_installation(self, server_name: str) -> ToolResult:
        """
        Check the status of a background installation.
        
        Args:
            server_name: Name of the server being installed
            
        Returns:
            ToolResult with the current status
        """
        if server_name not in self.background_installs:
            return ToolResult(
                tool=self.name,
                action="check_installation",
                status="ERROR",
                result={
                    "error": f"No background installation found for {server_name}",
                    "suggestion": "Make sure you've started an installation for this server."
                }
            )
        
        install_info = self.background_installs[server_name]
        task = install_info["task"]
        start_time = install_info["start_time"]
        server_id = install_info["server_id"]
        elapsed_time = time.time() - start_time
        
        # Check if the task has completed
        if task.done():
            # Remove from background installs
            del self.background_installs[server_name]
            
            # Check for exceptions
            try:
                server_info = task.result()
                
                # Store server information
                self.installed_servers[server_id] = server_info
                self._save_installed_servers()
                
                # Register the server with the agent if available
                registered = False
                if hasattr(self, 'agent') and self.agent is not None and hasattr(self.agent, 'register_mcp_server'):
                    try:
                        registered = await self.agent.register_mcp_server(server_info)
                        if registered:
                            self.logger.info(f"Registered server {server_id} with agent for immediate use")
                    except Exception as e:
                        self.logger.error(f"Failed to register server with agent: {e}")
                
                # Installation completed successfully
                return ToolResult(
                    tool=self.name,
                    action="install_mcp_server",
                    status="SUCCESS",
                    result={
                        "server_id": server_id,
                        "server_name": server_name,
                        "server_info": server_info,
                        "message": f"Background installation of MCP server {server_name} completed successfully",
                        "note": f"The server is now available as a tool with the name: {server_info['tool_name']}",
                        "registered_for_immediate_use": registered,
                        "installation_time": f"{elapsed_time:.1f} seconds"
                    }
                )
            except Exception as e:
                # Installation failed
                self.logger.error(f"Background installation of {server_name} failed: {e}")
                return ToolResult(
                    tool=self.name,
                    action="install_mcp_server",
                    status="ERROR",
                    result={
                        "error": f"Background installation of MCP server failed: {e}",
                        "suggestion": "Try installing again with a different approach or check system requirements."
                    }
                )
        else:
            # Task is still running
            return ToolResult(
                tool=self.name,
                action="check_installation",
                status="PENDING",
                result={
                    "server_id": server_id,
                    "server_name": server_name,
                    "message": f"Installation of {server_name} is still in progress",
                    "elapsed_time": f"{elapsed_time:.1f} seconds",
                    "background": True
                }
            )
    
    async def _install_from_npm(self, server_id: str, package_name: str, args: List[str], env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Install an MCP server from npm."""
        # Check if npx is available
        if not shutil.which("npx"):
            raise ToolExecutionException("npx is required to install npm MCP servers but is not found in PATH")
        
        # Set up server info
        server_path = os.path.join(self.servers_dir, server_id)
        tool_name = f"mcp_{server_id}"
        
        # Create command
        base_command = ["npx", package_name]
        if args:
            base_command.extend(args)
        
        # Create server info
        server_info = {
            "id": server_id,
            "name": package_name,
            "type": "npm",
            "command": "npx",
            "args": [package_name] + args,
            "env_vars": env_vars,
            "path": server_path,
            "tool_name": tool_name,
            "installed_at": str(asyncio.get_event_loop().time())
        }
        
        # Test the server by running once
        env = os.environ.copy()
        env.update(env_vars)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *base_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                self.logger.error(f"Error testing MCP server {package_name}: {stderr.decode()}")
                # Still continue since the server might be valid but just exited when run directly
            
            # Server appears valid
            return server_info
            
        except Exception as e:
            raise ToolExecutionException(f"Failed to test MCP server: {e}")
    
    async def _install_from_pypi(self, server_id: str, package_name: str, args: List[str], env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Install an MCP server from PyPI."""
        # Check if uv is available
        if not shutil.which("uv"):
            raise ToolExecutionException("uv is required to install Python MCP servers but is not found in PATH")
        
        # Set up server info
        server_path = os.path.join(self.servers_dir, server_id)
        tool_name = f"mcp_{server_id}"
        
        # Create commands for installation
        install_command = ["uv", "pip", "install", package_name]
        
        # Create server info
        server_info = {
            "id": server_id,
            "name": package_name,
            "type": "pypi",
            "command": "python",
            "args": ["-m", package_name] + args,
            "env_vars": env_vars,
            "path": server_path,
            "tool_name": tool_name,
            "installed_at": str(asyncio.get_event_loop().time())
        }
        
        # Install the package
        env = os.environ.copy()
        env.update(env_vars)
        
        try:
            # Install the package
            process = await asyncio.create_subprocess_exec(
                *install_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise ToolExecutionException(f"Failed to install Python package: {stderr.decode()}")
            
            # Test the server by running once
            run_command = ["python", "-m", package_name] + args
            process = await asyncio.create_subprocess_exec(
                *run_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()
            
            # Server appears valid
            return server_info
            
        except Exception as e:
            raise ToolExecutionException(f"Failed to install/test MCP server: {e}")
    
    async def _install_from_path(self, server_id: str, path: str, args: List[str], env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Install an MCP server from a local path."""
        # Check if the path is valid
        if not os.path.exists(path):
            raise ToolExecutionException(f"Path does not exist: {path}")
        
        # Determine if it's a Python or Node.js project
        is_node = os.path.exists(os.path.join(path, "package.json"))
        is_python = os.path.exists(os.path.join(path, "setup.py")) or os.path.exists(os.path.join(path, "pyproject.toml"))
        
        # Set up server info
        server_path = os.path.abspath(path)
        tool_name = f"mcp_{server_id}"
        
        if is_node:
            # Node.js project
            if not shutil.which("node"):
                raise ToolExecutionException("node is required to run Node.js MCP servers but is not found in PATH")
            
            # Create command
            command = "node"
            command_args = [os.path.join(server_path, "index.js")] + args
            server_type = "node"
            
        elif is_python:
            # Python project
            if not shutil.which("python"):
                raise ToolExecutionException("python is required to run Python MCP servers but is not found in PATH")
            
            # Create command
            command = "python"
            command_args = ["-m", os.path.basename(server_path)] + args
            server_type = "python"
            
        else:
            # Unknown project type, try to guess based on files
            if any(f.endswith(".py") for f in os.listdir(path)):
                command = "python" 
                command_args = [os.path.join(server_path, next(f for f in os.listdir(path) if f.endswith(".py")))] + args
                server_type = "python"
            elif any(f.endswith(".js") for f in os.listdir(path)):
                command = "node"
                command_args = [os.path.join(server_path, next(f for f in os.listdir(path) if f.endswith(".js")))] + args
                server_type = "node"
            else:
                raise ToolExecutionException(f"Could not determine project type for: {path}")
        
        # Create server info
        server_info = {
            "id": server_id,
            "name": os.path.basename(path),
            "type": server_type,
            "command": command,
            "args": command_args,
            "env_vars": env_vars,
            "path": server_path,
            "tool_name": tool_name,
            "installed_at": str(asyncio.get_event_loop().time())
        }
        
        # Test the server by running once
        env = os.environ.copy()
        env.update(env_vars)
        
        try:
            test_command = [command] + command_args
            process = await asyncio.create_subprocess_exec(
                *test_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()
            
            # Server appears valid (we don't check return code as the server might
            # exit normally when run directly without client connection)
            return server_info
            
        except Exception as e:
            raise ToolExecutionException(f"Failed to test MCP server: {e}")
    
    async def list_servers(self) -> Dict[str, Any]:
        """List all installed MCP servers."""
        return {
            "installed_servers": self.installed_servers
        }
    
    async def uninstall_server(self, server_id: str) -> Dict[str, Any]:
        """Uninstall an MCP server."""
        if server_id not in self.installed_servers:
            return {
                "status": "ERROR",
                "message": f"Server {server_id} is not installed"
            }
        
        # Stop the server if it's running
        if server_id in self.server_processes:
            try:
                self.server_processes[server_id].kill()
                del self.server_processes[server_id]
            except Exception as e:
                self.logger.error(f"Failed to stop server {server_id}: {e}")
        
        # Remove server from installed servers
        server_info = self.installed_servers.pop(server_id)
        self._save_installed_servers()
        
        return {
            "status": "SUCCESS",
            "message": f"Successfully uninstalled MCP server: {server_info['name']}"
        }
    
    async def reset(self) -> None:
        """Reset the tool state, stopping any running servers."""
        for server_id, process in self.server_processes.items():
            try:
                process.kill()
            except Exception as e:
                self.logger.error(f"Failed to stop server {server_id}: {e}")
        
        self.server_processes = {}

    async def check_installation_status(self, server_name: str) -> ToolResult:
        """
        Check the status of a server installation.
        
        Args:
            server_name: Name of the server to check
            
        Returns:
            ToolResult with the current status
        """
        # If it's a background installation, check that
        if server_name in self.background_installs:
            return await self._check_background_installation(server_name)
            
        # Check if it's already installed
        server_id = server_name.replace('/', '_').replace('@', '').replace('\\', '_')
        if server_id in self.installed_servers:
            return ToolResult(
                tool=self.name,
                action="check_installation",
                status="SUCCESS",
                result={
                    "server_id": server_id,
                    "server_name": server_name,
                    "server_info": self.installed_servers[server_id],
                    "message": f"MCP server {server_name} is already installed",
                    "note": f"The server is available as a tool with the name: {self.installed_servers[server_id]['tool_name']}"
                }
            )
        
        # Not installed or in progress
        return ToolResult(
            tool=self.name,
            action="check_installation",
            status="NOT_FOUND",
            result={
                "message": f"No installation found for MCP server {server_name}",
                "suggestion": "To install this server, call the mcp_installer tool with the server name."
            }
        )

class MCPServerTool(Tool):
    """Tool for interacting with an installed MCP server."""
    
    name = "mcp_server"
    description = "Interact with an installed Model Context Protocol (MCP) server."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The query to send to the MCP server"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, server_info: Dict[str, Any]):
        """Initialize the MCP server tool."""
        super().__init__()
        self.server_info = server_info
        self.name = f"mcp_{server_info['id']}"
        self.description = f"MCP server for {server_info['id']}"
        self.logger = get_tool_logger(self.name)
        
        # Initialize server process
        self.process = None
    
    async def _execute(self, query: str) -> ToolResult:
        """
        Execute a query against the MCP server.
        
        Args:
            query: The query to execute
            
        Returns:
            ToolResult with the server's response
        """
        if not self.process:
            await self._start_server()
        
        try:
            # Format the query for the MCP server
            formatted_query = {"query": query}
            
            # Send the query to the server via stdin
            if not self.process:
                raise ToolExecutionException("MCP server is not running")
                
            self.process.stdin.write(json.dumps(formatted_query).encode() + b'\n')
            await self.process.stdin.drain()
            
            # Read the response
            response_line = await self.process.stdout.readline()
            response = json.loads(response_line.decode())
            
            return ToolResult(
                tool=self.name,
                action="mcp_query",
                status="SUCCESS",
                result=response
            )
            
        except Exception as e:
            self.logger.error(f"Error communicating with MCP server: {e}")
            
            # Try to restart the server
            try:
                if self.process:
                    self.process.kill()
                await self._start_server()
            except Exception as restart_error:
                self.logger.error(f"Failed to restart MCP server: {restart_error}")
            
            return ToolResult(
                tool=self.name,
                action="mcp_query",
                status="ERROR",
                result={
                    "error": f"Failed to communicate with MCP server: {e}",
                    "suggestion": "The server may be unresponsive. Try again or consider reinstalling the server."
                }
            )
    
    async def _start_server(self) -> None:
        """Start the MCP server process."""
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.server_info.get("env_vars", {}))
            
            # Start the server process
            command = [self.server_info["command"]] + self.server_info["args"]
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.server_info.get("path")
            )
            
            self.logger.info(f"Started MCP server: {self.server_info['name']} (PID: {self.process.pid})")
            
        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            raise ToolExecutionException(f"Failed to start MCP server: {e}")
    
    async def reset(self) -> None:
        """Reset the tool state, stopping the server process."""
        if self.process:
            try:
                self.process.kill()
                self.process = None
            except Exception as e:
                self.logger.error(f"Failed to stop MCP server: {e}") 