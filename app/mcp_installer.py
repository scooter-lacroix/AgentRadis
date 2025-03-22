"""
MCP (Machine Capability Provider) Installer
Manages installation of external tools and libraries for Radis
"""

import os
import sys
import subprocess
import json
import shutil
import platform
from pathlib import Path
from typing import Dict, List, Any, Union, Optional

from app.logger import logger

class MCPInstaller:
    """
    Machine Capability Provider (MCP) Installer
    
    Handles the installation and management of external tools and libraries
    that extend the capabilities of Radis.
    """
    
    # Default installation directory for MCP tools
    DEFAULT_INSTALL_DIR = os.path.expanduser("~/.agentradis/mcp")
    
    # Configuration file for tracking installed MCPs
    CONFIG_FILE = os.path.expanduser("~/.agentradis/mcp-config.json")
    
    def __init__(self, install_dir: Optional[str] = None):
        """
        Initialize the MCP Installer.
        
        Args:
            install_dir: Custom installation directory (optional)
        """
        self.install_dir = install_dir or self.DEFAULT_INSTALL_DIR
        self._ensure_dirs()
        self.config = self._load_config()
        
    def _ensure_dirs(self):
        """Ensure the MCP directories exist."""
        os.makedirs(self.install_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        
    def _load_config(self) -> Dict:
        """Load the MCP configuration file."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse MCP config file: {self.CONFIG_FILE}")
                return {"installed": {}}
        return {"installed": {}}
        
    def _save_config(self):
        """Save the MCP configuration file."""
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
            
    def is_installed(self, mcp_name: str) -> bool:
        """
        Check if an MCP is installed.
        
        Args:
            mcp_name: Name of the MCP to check
            
        Returns:
            True if installed, False otherwise
        """
        return mcp_name in self.config["installed"]
        
    def get_installed_mcps(self) -> Dict[str, Dict]:
        """
        Get all installed MCPs.
        
        Returns:
            Dictionary of installed MCPs with their metadata
        """
        return self.config["installed"]
        
    def install_realtimestt(self, force: bool = False) -> bool:
        """
        Install the RealtimeSTT library for speech recognition.
        
        Args:
            force: Force reinstallation if already installed
            
        Returns:
            True if installation successful, False otherwise
        """
        mcp_name = "realtimestt"
        
        if self.is_installed(mcp_name) and not force:
            logger.info(f"{mcp_name} is already installed")
            return True
            
        logger.info(f"Installing {mcp_name}...")
        
        try:
            # Install RealtimeSTT from PyPI
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "realtimestt==0.1.6"], 
                capture_output=True,
                text=True,
                check=True
            )
            
            # Record the installation
            self.config["installed"][mcp_name] = {
                "version": "0.1.6",
                "path": "python package",
                "installed_at": "pip",
                "description": "Real-time speech recognition library",
            }
            self._save_config()
            
            logger.info(f"Successfully installed {mcp_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {mcp_name}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error installing {mcp_name}: {str(e)}")
            return False
            
    def install_realtimetts(self, force: bool = False) -> bool:
        """
        Install the RealtimeTTS library for text-to-speech.
        
        Args:
            force: Force reinstallation if already installed
            
        Returns:
            True if installation successful, False otherwise
        """
        mcp_name = "realtimetts"
        
        if self.is_installed(mcp_name) and not force:
            logger.info(f"{mcp_name} is already installed")
            return True
            
        logger.info(f"Installing {mcp_name}...")
        
        try:
            # Install RealtimeTTS from PyPI
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "realtimetts==0.1.0"], 
                capture_output=True,
                text=True,
                check=True
            )
            
            # Record the installation
            self.config["installed"][mcp_name] = {
                "version": "0.1.0",
                "path": "python package",
                "installed_at": "pip",
                "description": "Real-time text-to-speech library",
            }
            self._save_config()
            
            logger.info(f"Successfully installed {mcp_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {mcp_name}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error installing {mcp_name}: {str(e)}")
            return False
            
    def install_speech_capabilities(self, force: bool = False) -> Dict[str, bool]:
        """
        Install all speech-related capabilities (STT and TTS).
        
        Args:
            force: Force reinstallation if already installed
            
        Returns:
            Dictionary mapping capability names to installation success status
        """
        results = {}
        
        # Install RealtimeSTT
        results["realtimestt"] = self.install_realtimestt(force)
        
        # Install RealtimeTTS
        results["realtimetts"] = self.install_realtimetts(force)
        
        return results
        
    def uninstall(self, mcp_name: str) -> bool:
        """
        Uninstall an MCP.
        
        Args:
            mcp_name: Name of the MCP to uninstall
            
        Returns:
            True if uninstallation successful, False otherwise
        """
        if not self.is_installed(mcp_name):
            logger.info(f"{mcp_name} is not installed")
            return True
            
        logger.info(f"Uninstalling {mcp_name}...")
        
        try:
            # Handle specific uninstallation logic based on MCP type
            if mcp_name == "realtimestt":
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y", "realtimestt"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            elif mcp_name == "realtimetts":
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y", "realtimetts"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                # Generic uninstallation for other MCPs
                mcp_path = self.config["installed"][mcp_name].get("path")
                if mcp_path and mcp_path != "python package" and os.path.exists(mcp_path):
                    if os.path.isdir(mcp_path):
                        shutil.rmtree(mcp_path)
                    else:
                        os.remove(mcp_path)
            
            # Remove from config
            del self.config["installed"][mcp_name]
            self._save_config()
            
            logger.info(f"Successfully uninstalled {mcp_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error uninstalling {mcp_name}: {str(e)}")
            return False 