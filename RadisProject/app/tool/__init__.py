from app.tool.base import BaseTool
from app.tool.bash import BashTool
from app.tool.file_tool import FileTool
from app.tool.code_gen import CodeGenTool
from app.tool.crypto import CryptoTool
from app.tool.python_tool import PythonTool
from app.core.tool_registry import get_tool_registry
from app.tool.str_replace import StrReplaceEditor
from app.tool.thinking import ThinkingTool
from app.tool.planning import PlanningTool
from app.tool.weather import WeatherTool
from app.tool.web_search import WebSearch
from app.tool.web_tool import WebTool
from app.tool.time_tool import TimeTool

__all__ = [
    "BaseTool",
    "BashTool",
    "CodeGenTool",
    "CryptoTool",
    "FileTool",
    "get_tool_registry",
    "PythonTool",
    "PlanningTool",
    "StrReplaceEditor",
    "ThinkingTool",
    "WeatherTool",
    "WebSearch",
    "TimeTool",
    "WebTool",
]

# Register default tools
# Initialize tool registry
registry = get_tool_registry()

# Register default tools with descriptive names
if not registry.has_tool("bash"):
    registry.register_tool("bash", BashTool())
if not registry.has_tool("file"):
    registry.register_tool("file", FileTool())
if not registry.has_tool("python"):
    registry.register_tool("python", PythonTool())
if not registry.has_tool("str_replace"):
    registry.register_tool("str_replace", StrReplaceEditor())
if not registry.has_tool("thinking"):
    registry.register_tool("thinking", ThinkingTool())
if not registry.has_tool("web_search"):
    registry.register_tool("web_search", WebSearch())
if not registry.has_tool("web"):
    registry.register_tool("web", WebTool())
if not registry.has_tool("code_gen"):
    registry.register_tool("code_gen", CodeGenTool())
if not registry.has_tool("crypto"):
    registry.register_tool("crypto", CryptoTool())
if not registry.has_tool("planning"):
    registry.register_tool("planning", PlanningTool())
if not registry.has_tool("time"):
    registry.register_tool("time", TimeTool())
if not registry.has_tool("weather"):
    registry.register_tool("weather", WeatherTool())
