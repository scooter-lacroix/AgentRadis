import pytest
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from io import StringIO
from app.display import ArtifactDisplay, ToolDisplay, ProgressDisplay, setup_display
import re

@pytest.fixture
def console():
    """Create a test console that captures output"""
    return Console(file=StringIO(), force_terminal=True, color_system=None)

def strip_ansi(text):
    """Remove ANSI escape sequences from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def test_artifact_display_code_preview(monkeypatch, console):
    """Test code preview artifact display"""
    monkeypatch.setattr('app.display.console', console)
    
    code = """def test_function():
    return "Hello World"
    """
    ArtifactDisplay.code_preview(code, "python")
    output = strip_ansi(console.file.getvalue())
    
    assert "Code Preview" in output
    assert "test_function" in output
    assert "Hello World" in output

def test_artifact_display_web_preview(monkeypatch, console):
    """Test web preview artifact display"""
    monkeypatch.setattr('app.display.console', console)
    
    html = "<html><body><h1>Test</h1></body></html>"
    ArtifactDisplay.web_preview(html)
    output = strip_ansi(console.file.getvalue())
    
    assert "Web Preview" in output
    assert all(tag in output for tag in ["<html>", "<body>", "<h1>"])

def test_artifact_display_project_structure(monkeypatch, console):
    """Test project structure artifact display"""
    monkeypatch.setattr('app.display.console', console)
    
    structure = {
        "src": {
            "main.py": None,
            "utils": {
                "helper.py": None
            }
        },
        "README.md": None
    }
    ArtifactDisplay.project_structure(structure)
    output = strip_ansi(console.file.getvalue())
    
    assert "Project Structure" in output
    assert "📁 src" in output
    assert "📄 main.py" in output
    assert "📄 README.md" in output

def test_tool_display_show_tools(monkeypatch, console):
    """Test tools display"""
    monkeypatch.setattr('app.display.console', console)
    
    class MockTool:
        def __init__(self, name, description, category):
            self.name = name
            self.description = description
            self.category = category
    
    tools = [
        MockTool("TestTool", "A test tool", "Testing"),
        MockTool("WebTool", "A web tool", "Web")
    ]
    
    ToolDisplay.show_tools(tools)
    output = strip_ansi(console.file.getvalue())
    
    assert "Available Tools" in output
    assert "TestTool" in output
    assert "WebTool" in output
    assert "Testing" in output
    assert "Web" in output

def test_tool_display_show_tool_call(monkeypatch, console):
    """Test tool call display"""
    monkeypatch.setattr('app.display.console', console)
    
    args = {"param1": "value1", "param2": "value2"}
    ToolDisplay.show_tool_call("TestTool", args)
    output = strip_ansi(console.file.getvalue())
    
    assert "Using TestTool" in output
    assert "param1" in output
    assert "value1" in output
    assert "param2" in output
    assert "value2" in output

def test_tool_display_show_tool_result_success(monkeypatch, console):
    """Test successful tool result display"""
    monkeypatch.setattr('app.display.console', console)
    
    result = {"status": "success", "data": "test data"}
    ToolDisplay.show_tool_result(result, True)
    output = strip_ansi(console.file.getvalue())
    
    assert "✅ Success" in output
    assert "test data" in output

def test_tool_display_show_tool_result_error(monkeypatch, console):
    """Test error tool result display"""
    monkeypatch.setattr('app.display.console', console)
    
    result = "Error occurred"
    ToolDisplay.show_tool_result(result, False)
    output = strip_ansi(console.file.getvalue())
    
    assert "❌ Error" in output
    assert "Error occurred" in output

@pytest.mark.asyncio
async def test_progress_display_thinking(monkeypatch, console):
    """Test thinking progress display"""
    monkeypatch.setattr('app.display.console', console)
    
    # Mock Progress class to avoid actual progress animation
    class MockProgress:
        def __init__(self, *args, **kwargs):
            pass
            
        def __enter__(self):
            return self
            
        def __exit__(self, *args):
            pass
            
        def add_task(self, description, total=None):
            console.print(description)
            return 1
            
        def update(self, task_id, completed=None):
            pass
    
    monkeypatch.setattr('app.display.Progress', MockProgress)
    
    progress = ProgressDisplay()
    progress.show_thinking()
    output = strip_ansi(console.file.getvalue())
    
    assert "🤔 Thinking" in output

@pytest.mark.asyncio
async def test_progress_display_executing(monkeypatch, console):
    """Test executing progress display"""
    monkeypatch.setattr('app.display.console', console)
    
    # Mock Progress class to avoid actual progress animation
    class MockProgress:
        def __init__(self, *args, **kwargs):
            pass
            
        def __enter__(self):
            return self
            
        def __exit__(self, *args):
            pass
            
        def add_task(self, description, total=None):
            console.print(description)
            return 1
            
        def update(self, task_id, completed=None):
            pass
    
    monkeypatch.setattr('app.display.Progress', MockProgress)
    
    progress = ProgressDisplay()
    progress.show_executing("test action")
    output = strip_ansi(console.file.getvalue())
    
    assert "⚡ Executing: test action" in output

def test_setup_display(monkeypatch, console):
    """Test display setup"""
    monkeypatch.setattr('app.display.console', console)
    
    setup_display()
    output = strip_ansi(console.file.getvalue())
    
    assert "AgentRadis" in output
    assert "Your AI Assistant" in output 