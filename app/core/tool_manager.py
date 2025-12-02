"""
Tool Manager for DOKAPON! Sword of Fury Tools
Manages paths to bundled external tools (FFmpeg, opusenc).

Author: DiNaSoR
License: Free to use and modify
"""

import os
import sys
import subprocess
import platform
from typing import Dict, Optional, Tuple
from pathlib import Path


class ToolManager:
    """
    Manages external tools used by the application.
    
    Tools are expected to be bundled in the app/tools directory for distribution,
    but will fall back to system PATH if not found.
    """
    
    # Tool definitions: name -> (subfolder, executable_name)
    TOOLS = {
        "ffmpeg": ("ffmpeg", "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"),
        "ffprobe": ("ffmpeg", "ffprobe.exe" if platform.system() == "Windows" else "ffprobe"),
        "opusenc": ("opusenc", "opusenc.exe" if platform.system() == "Windows" else "opusenc"),
    }
    
    _instance = None
    _tool_paths: Dict[str, str] = {}
    
    def __new__(cls):
        """Singleton pattern to ensure consistent tool paths."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._discover_tools()
    
    def _get_tools_dir(self) -> str:
        """Get the path to the tools directory."""
        # When running from source
        if getattr(sys, 'frozen', False):
            # Running as compiled executable (PyInstaller)
            base_dir = os.path.dirname(sys.executable)
        else:
            # Running from source
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        return os.path.join(base_dir, "tools")
    
    def _discover_tools(self) -> None:
        """Discover available tools in bundled directory or system PATH."""
        tools_dir = self._get_tools_dir()
        
        for tool_name, (subfolder, exe_name) in self.TOOLS.items():
            # First check bundled location
            bundled_path = os.path.join(tools_dir, subfolder, exe_name)
            
            if os.path.exists(bundled_path):
                self._tool_paths[tool_name] = bundled_path
            else:
                # Fall back to system PATH
                system_path = self._find_in_path(exe_name)
                if system_path:
                    self._tool_paths[tool_name] = system_path
                else:
                    # Store just the name, will try to use it anyway
                    self._tool_paths[tool_name] = exe_name.replace(".exe", "") if platform.system() != "Windows" else exe_name
    
    def _find_in_path(self, exe_name: str) -> Optional[str]:
        """Find an executable in the system PATH."""
        try:
            if platform.system() == "Windows":
                # Use 'where' on Windows
                result = subprocess.run(
                    ["where", exe_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip().split('\n')[0]
            else:
                # Use 'which' on Unix-like systems
                result = subprocess.run(
                    ["which", exe_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except:
            pass
        return None
    
    @classmethod
    def get_instance(cls) -> 'ToolManager':
        """Get the singleton instance."""
        return cls()
    
    def get_ffmpeg_path(self) -> str:
        """Get path to ffmpeg executable."""
        return self._tool_paths.get("ffmpeg", "ffmpeg")
    
    def get_ffprobe_path(self) -> str:
        """Get path to ffprobe executable."""
        return self._tool_paths.get("ffprobe", "ffprobe")
    
    def get_opusenc_path(self) -> str:
        """Get path to opusenc executable."""
        return self._tool_paths.get("opusenc", "opusenc")
    
    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """Get path to a specific tool by name."""
        return self._tool_paths.get(tool_name)
    
    def verify_tool(self, tool_name: str) -> Tuple[bool, str]:
        """
        Verify that a specific tool is available and working.
        
        Args:
            tool_name: Name of tool to verify
            
        Returns:
            Tuple of (available, message)
        """
        tool_path = self._tool_paths.get(tool_name)
        if not tool_path:
            return False, f"Tool '{tool_name}' not configured"
        
        try:
            # Try to run with --version or -version
            for version_flag in ["--version", "-version", "-v"]:
                try:
                    result = subprocess.run(
                        [tool_path, version_flag],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        version_line = result.stdout.strip().split('\n')[0]
                        return True, version_line
                except:
                    continue
            
            return False, f"Tool '{tool_name}' found but not responding"
            
        except FileNotFoundError:
            return False, f"Tool '{tool_name}' not found at {tool_path}"
        except subprocess.TimeoutExpired:
            return False, f"Tool '{tool_name}' timed out"
        except Exception as e:
            return False, f"Error checking '{tool_name}': {e}"
    
    def verify_all_tools(self) -> Dict[str, Tuple[bool, str]]:
        """
        Verify all registered tools.
        
        Returns:
            Dictionary of tool_name -> (available, message)
        """
        results = {}
        for tool_name in self.TOOLS.keys():
            results[tool_name] = self.verify_tool(tool_name)
        return results
    
    def get_tools_status(self) -> Dict[str, dict]:
        """
        Get detailed status of all tools.
        
        Returns:
            Dictionary with tool information
        """
        status = {}
        for tool_name in self.TOOLS.keys():
            path = self._tool_paths.get(tool_name, "")
            available, message = self.verify_tool(tool_name)
            
            is_bundled = path and os.path.exists(path) and self._get_tools_dir() in path
            
            status[tool_name] = {
                "path": path,
                "available": available,
                "message": message,
                "bundled": is_bundled,
            }
        return status
    
    def is_ffmpeg_available(self) -> bool:
        """Quick check if FFmpeg is available."""
        available, _ = self.verify_tool("ffmpeg")
        return available
    
    def is_opusenc_available(self) -> bool:
        """Quick check if opusenc is available."""
        available, _ = self.verify_tool("opusenc")
        return available


# Convenience functions for direct import
def get_ffmpeg_path() -> str:
    """Get path to ffmpeg executable."""
    return ToolManager.get_instance().get_ffmpeg_path()


def get_ffprobe_path() -> str:
    """Get path to ffprobe executable."""
    return ToolManager.get_instance().get_ffprobe_path()


def get_opusenc_path() -> str:
    """Get path to opusenc executable."""
    return ToolManager.get_instance().get_opusenc_path()


def verify_tools() -> Dict[str, bool]:
    """
    Verify all tools and return simple available/not available status.
    
    Returns:
        Dictionary of tool_name -> is_available
    """
    results = ToolManager.get_instance().verify_all_tools()
    return {name: status[0] for name, status in results.items()}

