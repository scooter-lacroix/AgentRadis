from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.live import Live
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.box import DOUBLE
from rich.style import Style
from rich.text import Text
import time
import json
import random

console = Console()

class ArtifactDisplay:
    """Handles the display of various artifacts during agent execution"""
    
    @staticmethod
    def code_preview(code: str, language: str = "python"):
        """Display code with syntax highlighting"""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Code Preview", border_style="green"))
    
    @staticmethod
    def web_preview(html: str):
        """Display a preview of web content"""
        # In CLI mode, show formatted HTML
        syntax = Syntax(html, "html", theme="monokai")
        console.print(Panel(syntax, title="Web Preview", border_style="blue"))
    
    @staticmethod
    def project_structure(structure: Dict):
        """Display project structure in a tree-like format"""
        table = Table(show_header=False, box=None)
        table.add_column("Structure")
        
        def add_items(items, prefix=""):
            for key, value in items.items():
                if isinstance(value, dict):
                    table.add_row(f"{prefix}📁 {key}")
                    add_items(value, prefix + "  ")
                else:
                    table.add_row(f"{prefix}📄 {key}")
        
        add_items(structure)
        console.print(Panel(table, title="Project Structure", border_style="yellow"))

    @staticmethod
    def format_result(result: str, title: str = "Result"):
        """Format a result with a nice border and title"""
        result_panel = Panel(
            result,
            title=title,
            border_style="bright_blue",
            box=DOUBLE,
            padding=(1, 2)
        )
        console.print(result_panel)

class ToolDisplay:
    """Handles the display of tools and their outputs"""
    
    @staticmethod
    def show_tools(tools: List[Any]):
        """Display available tools in an organized panel with proper formatting"""
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Tool", style="cyan")
        table.add_column("Description")
        table.add_column("Category", style="green")
        
        for tool in tools:
            name = tool.name if hasattr(tool, 'name') else "Unnamed Tool"
            desc = tool.description if hasattr(tool, 'description') else ""
            category = getattr(tool, 'category', 'General')
            table.add_row(name, desc, category)
        
        # Create the capabilities panel with exact formatting
        console.print("╔════════════════════════════════ 🌟 Radis's Capabilities 🌟 ═════════════════════════════════╗", style="bright_green")
        console.print("║                                                                                             ║", style="bright_green")
        console.print("║                                                                                             ║", style="bright_green")
        console.print("║  Radis Capabilities:                                                                        ║", style="bright_green")
        console.print("║                                                                                             ║", style="bright_green")
        console.print("║  • Web Search: Search the internet for information                                          ║", style="bright_green")
        console.print("║  • File Operations: Create, read, write, and manage files                                   ║", style="bright_green")
        console.print("║  • Terminal Access: Run commands in the terminal                                            ║", style="bright_green")
        console.print("║  • Python Execution: Run Python code                                                        ║", style="bright_green")
        console.print("║  • Browser Automation: Control a web browser                                                ║", style="bright_green")
        console.print("║  • Planning: Create and manage execution plans                                              ║", style="bright_green")
        console.print("║                                                                                             ║", style="bright_green")
        console.print("╚═════════════════════════════════════════════════════════════════════════════════════════════╝", style="bright_green")
        
        # Display the tools table with proper styling
        tools_panel = Panel(
            table,
            title="🛠️ Available Tools",
            border_style="green"
        )
        console.print(tools_panel)
    
    @staticmethod
    def show_tool_call(tool_name: str, args: Dict[str, Any]):
        """Display tool call in a visually appealing way"""
        args_table = Table(show_header=False, box=None)
        args_table.add_column("Argument", style="cyan")
        args_table.add_column("Value")
        
        for key, value in args.items():
            args_table.add_row(key, str(value))
        
        console.print(Panel(args_table, title=f"🔧 Using {tool_name}", border_style="blue"))
        # Add separator after tool call
        console.print("=" * console.width, style="dim")
    
    @staticmethod
    def show_tool_result(result: Any, success: bool = True):
        """Display tool execution result"""
        style = "green" if success else "red"
        title = "✅ Success" if success else "❌ Error"
        
        if isinstance(result, (dict, list)):
            result = json.dumps(result, indent=2)
        
        console.print(Panel(str(result), title=title, border_style=style))
        # Add separator after tool result
        console.print("=" * console.width, style="dim")

class ProgressDisplay:
    """Handles progress and status displays"""
    
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        )
    
    def show_thinking(self):
        """Display thinking animation"""
        with self.progress:
            task = self.progress.add_task("🤔 Thinking...", total=1)
            self.progress.update(task, completed=1)
    
    def show_executing(self, action: str):
        """Display execution progress"""
        with self.progress:
            task = self.progress.add_task(f"⚡ Executing: {action}", total=1)
            self.progress.update(task, completed=1)

class PlanFormatter:
    """Handles the formatting of plans with a highlighted box"""
    
    @staticmethod
    def format_plan(plan_text: str):
        """Format a plan with a highlighted box and nice styling"""
        plan_panel = Panel(
            plan_text,
            title="📝 Execution Plan",
            subtitle="Your request is being processed according to this plan",
            border_style="bright_yellow",
            box=DOUBLE,
            padding=(1, 2),
            highlight=True
        )
        console.print(plan_panel)

def generate_starry_background():
    """Generate a starry background for the banner"""
    stars = ""
    for _ in range(10):
        # Create random stars at random positions
        x = random.randint(5, 45)
        y = random.randint(1, 6)
        star_type = random.choice(["*", "✧", "★", "☆", "✦"])
        stars += f"{' ' * x}{star_type}\n"
    return stars

def print_ascii_banner_with_stars():
    """Print a fancy ASCII banner with stars as specified in the example"""
    # Create multi-color ASCII art for AGENT RADIS using Rich's Text object
    agent_radis_text = Text()
    
    # Line 1 - Header
    agent_radis_text.append("     _      _____  _____  _   _  _____    ____   _    ____  _  _____\n", style="bright_cyan")
    
    # Line 2 - A G E N T  R A D I S
    line2 = "     / /    / ____|| ____|| / | ||_   _|  |  _ / / /  |  _ /| |/ /___ /\n"
    for i, char in enumerate(line2):
        if char == '/':
            agent_radis_text.append(char, style="bright_magenta")
        else:
            agent_radis_text.append(char, style="bright_cyan")
    
    # Line 3
    line3 = "    / _ /  | |  _  |  _|  |  /| |  | |    | |_) / _ / | | | | ' /  __) |\n"
    for i, char in enumerate(line3):
        if char == '/':
            agent_radis_text.append(char, style="bright_magenta")
        else:
            agent_radis_text.append(char, style="bright_cyan")
    
    # Line 4
    line4 = "   / ___ / | |_| | | |___ | |/  |  | |    |  _ / ___ /| |_| | . / / __/\n"
    for i, char in enumerate(line4):
        if char == '/':
            agent_radis_text.append(char, style="bright_magenta")
        else:
            agent_radis_text.append(char, style="bright_cyan")
    
    # Line 5
    line5 = "  /_/   /_/ /____| |_____||_| /_|  |_|    |_| /_/   /_/____/|_|/_/_____/"
    for i, char in enumerate(line5):
        if char == '/' or char == '_':
            agent_radis_text.append(char, style="bright_magenta")
        else:
            agent_radis_text.append(char, style="bright_cyan")
    
    # Create the panel with the ASCII art
    panel = Panel(
        agent_radis_text,
        title=" AGENT RADIS ",
        title_align="center",
        subtitle=" Flow Runner ",
        subtitle_align="center",
        border_style="bright_cyan",
        padding=(1, 2),
        width=93,
    )
    
    # Print the panel
    console.print(panel)
    
    # Print the exact star pattern
    console.print("              ✧", style="bright_white")
    console.print("                                                    ✧", style="bright_white")
    console.print("     ✧", style="bright_white")
    console.print("                                                         ✧", style="bright_white")
    console.print("                           ✧", style="bright_white")

def setup_display():
    """Initialize display settings"""
    console.clear()
    print_ascii_banner_with_stars()
    console.print("\nYour gateway to the internet awaits and Radis will be your guide. Embrace the cosmos.", style="italic cyan")
    console.print("Type 'exit' to quit.\n", style="dim")
    console.print("=" * console.width, style="dim") 