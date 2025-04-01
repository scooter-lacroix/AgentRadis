from typing import Optional, Any, List, ContextManager
import sys
import shutil
import time
import threading
import logging
from enum import Enum
from dataclasses import dataclass
import colorama
from colorama import Fore, Back, Style
from rich.console import Console
from rich.panel import Panel
import rich.box
from rich.style import Style as RichStyle
from contextlib import contextmanager
from types import TracebackType
from typing import Type

# Initialize colorama for cross-platform color support
colorama.init()


class ThinkingDisplay:
    """Manages the thinking animation and tool usage display."""

    def __init__(self):
        self._thinking = False
        self._thinking_thread = None
        self._tools_used: List[str] = []
        self._steps_completed: List[str] = []

    def start_thinking(self):
        """Start the thinking animation."""
        logging.info("Starting thinking animation display")
        self._thinking = True
        self._thinking_thread = threading.Thread(target=self._animate_thinking)
        self._thinking_thread.daemon = True
        self._thinking_thread.start()

    def stop_thinking(self):
        """Stop the thinking animation."""
        logging.info("Stopping thinking animation display")
        self._thinking = False
        if self._thinking_thread:
            self._thinking_thread.join()
            print("\r" + " " * 20 + "\r", end="", flush=True)  # Clear the line

    def _animate_thinking(self):
        """Animate the thinking process."""
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while self._thinking:
            frame = frames[i % len(frames)]
            print(
                f"\r{Fore.CYAN}[{frame}] Thinking...{Style.RESET_ALL}",
                end="",
                flush=True,
            )
            time.sleep(0.1)
            i += 1

    def add_tool_used(self, tool_name: str):
        """Record a tool that was used."""
        if tool_name not in self._tools_used:
            self._tools_used.append(tool_name)

    def add_step_completed(self, step: str):
        """Record a completed step."""
        self._steps_completed.append(step)

    def show_summary(self):
        """Display a summary of tools used and steps completed."""
        if not self._tools_used and not self._steps_completed:
            return

        console = Console()
        console.print("\n[bold yellow]Operation Summary:[/bold yellow]")

        if self._tools_used:
            console.print("\n[bold]Tools Used:[/bold]")
            for tool in self._tools_used:
                console.print(f"  ✓ {tool}")

        if self._steps_completed:
            console.print("\n[bold]Steps Completed:[/bold]")
            for step in self._steps_completed:
                console.print(f"  ✓ {step}")

        console.print("\n" + "=" * shutil.get_terminal_size().columns + "\n")

    def reset(self):
        """Reset the tracking of tools and steps."""
        self._tools_used.clear()
        self._steps_completed.clear()


class ThinkingHandler(logging.Handler):
    """Custom logging handler that shows a thinking animation for debug logs."""

    def __init__(self):
        super().__init__()
        self._thinking_display = ThinkingDisplay()
        self._active = False

    def emit(self, record):
        """Handle the log record."""
        # Only handle debug records
        if record.levelno == logging.DEBUG:
            if not self._active:
                self._thinking_display.start_thinking()
                self._active = True

            # If the message contains tool or step information, record it
            msg = record.getMessage().lower()
            if "using tool:" in msg:
                tool = msg.split("using tool:", 1)[1].strip()
                self._thinking_display.add_tool_used(tool)
            elif "completed step:" in msg:
                step = msg.split("completed step:", 1)[1].strip()
                self._thinking_display.add_step_completed(step)
        else:
            # For non-debug messages, stop the thinking animation
            if self._active:
                self._thinking_display.stop_thinking()
                self._active = False
            # Show the actual log message
            print(self.format(record))

    def stop(self):
        """Stop the thinking animation and show summary."""
        if self._active:
            self._thinking_display.stop_thinking()
            self._thinking_display.show_summary()
            self._thinking_display.reset()
            self._active = False


class DisplayLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


@dataclass
class DisplayConfig:
    """Configuration for display components."""

    show_timestamps: bool = True
    color_output: bool = True
    debug_mode: bool = False
    progress_bar_width: int = 50


class ToolDisplay:
    """Handles the display of tools and their outputs"""

    def __init__(self, config: Optional[DisplayConfig] = None):
        """Initialize ToolDisplay with optional configuration"""
        self.config = config or DisplayConfig()
        self.console = Console()

    def show_tools(self, tools: List[Any]):
        pass

    def tool_start(self, tool_name: str, description: str) -> None:
        """Display tool operation start."""
        print(
            f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} Starting {Fore.GREEN}{tool_name}{Style.RESET_ALL}: {description}"
        )

    def tool_complete(self, tool_name: str, result: Any) -> None:
        """Display tool operation completion."""
        print(
            f"{Fore.CYAN}[TOOL]{Style.RESET_ALL} Completed {Fore.GREEN}{tool_name}{Style.RESET_ALL}"
        )
        if self.config.debug_mode:
            print(f"{Fore.BLUE}Result:{Style.RESET_ALL} {result}")

    def tool_error(self, tool_name: str, error: Exception) -> None:
        """Display tool operation error."""
        print(
            f"{Fore.RED}[ERROR]{Style.RESET_ALL} In {tool_name}: {error}",
            file=sys.stderr,
        )


class ArtifactDisplay:
    """Handles the display of different types of artifacts."""

    def __init__(self, config: Optional[DisplayConfig] = None):
        self.config = config or DisplayConfig()

    def show_code(self, code: str, language: str = "python") -> None:
        """Display code artifacts with syntax highlighting."""
        print(f"{Fore.YELLOW}```{language}{Style.RESET_ALL}")
        print(code)
        print(f"{Fore.YELLOW}```{Style.RESET_ALL}")

    def show_file_diff(self, file_path: str, diff: str) -> None:
        """Display file differences."""
        print(f"{Fore.CYAN}File: {file_path}{Style.RESET_ALL}")
        for line in diff.split("\n"):
            if line.startswith("+"):
                print(f"{Fore.GREEN}{line}{Style.RESET_ALL}")
            elif line.startswith("-"):
                print(f"{Fore.RED}{line}{Style.RESET_ALL}")
            else:
                print(line)

    def show_data(self, data: Any, title: Optional[str] = None) -> None:
        """Display data artifacts."""
        if title:
            print(f"{Fore.CYAN}{title}:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{data}{Style.RESET_ALL}")


class ProgressDisplayError(Exception):
    """Custom exception for ProgressDisplay errors."""

    pass


class ProgressDisplay:
    """Handles the display of progress indicators.

    This class provides methods for tracking and displaying progress of operations.
    It includes robust error handling to ensure proper usage and feedback.

    Attributes:
        config (DisplayConfig): Display configuration settings
        _current (int): Current progress value
        _total (int): Total progress value (target)
        _message (str): Message to display with the progress bar
        _active (bool): Whether the progress tracking is active
    """

    def __init__(self, config: Optional[DisplayConfig] = None):
        """Initialize a new ProgressDisplay instance.

        Args:
            config (Optional[DisplayConfig]): Display configuration settings.
              If not provided, default settings will be used.
        """
        self.config = config or DisplayConfig()
        self._current = 0
        self._total = 0
        self._message = ""
        self._active = False

    def start(self, total: int, message: str) -> None:
        """Initialize progress tracking with validation.

        Args:
            total (int): Total number of steps for the operation.
            message (str): Message to display with the progress bar.

        Raises:
            ProgressDisplayError: If total is less than 0 or message is empty.

        Note:
            If total is 0, the progress bar will be initialized but no visual
            progress will be shown until total is set to a positive value.
        """
        # Validate inputs
        if total < 0:
            raise ProgressDisplayError("Total progress steps cannot be negative")
        if not message:
            raise ProgressDisplayError("Progress message cannot be empty")

        self._current = 0
        self._total = total
        self._message = message
        self._active = True
        self._update_progress()

    def advance(self, amount: int = 1) -> None:
        """Advance progress by the specified amount with validation.

        Args:
            amount (int): Amount to advance the progress. Default is 1.

        Raises:
            ProgressDisplayError: If progress tracking is not active or if amount is negative.
        """
        if not self._active:
            raise ProgressDisplayError("Cannot advance progress before calling start()")

        if amount < 0:
            raise ProgressDisplayError("Cannot advance progress by a negative amount")

        # Ensure we don't exceed total
        self._current = min(self._current + amount, self._total)
        self._update_progress()

    def complete(self) -> None:
        """Mark progress as complete with validation.

        Raises:
            ProgressDisplayError: If progress tracking is not active.
        """
        if not self._active:
            raise ProgressDisplayError(
                "Cannot complete progress before calling start()"
            )

        self._current = self._total
        self._update_progress()
        self._active = False
        print()  # New line after completion

    def reset(self) -> None:
        """Reset the progress tracking.

        This will clear the current progress state without displaying
        any updates. Useful when cancelling an operation.
        """
        self._current = 0
        self._total = 0
        self._message = ""
        self._active = False

    def _update_progress(self) -> None:
        """Update the progress display with error handling.

        This internal method handles the actual display update with
        proper error handling for edge cases.
        """
        # Handle edge case where total is 0
        if self._total == 0:
            # Just show the message without a progress bar
            print(f"\r{self._message}", end="", flush=True)
            return

        try:
            percentage = (self._current / self._total) * 100
            bar_width = self.config.progress_bar_width
            filled_width = int(bar_width * self._current / self._total)

            # Ensure filled_width is valid
            filled_width = max(0, min(filled_width, bar_width))

            bar = "=" * filled_width + "-" * (bar_width - filled_width)
            print(f"\r{self._message}: [{bar}] {percentage:.1f}%", end="", flush=True)
        except ZeroDivisionError:
            # This should not happen due to our check above, but as a fallback
            print(
                f"\r{self._message}: [{'?' * self.config.progress_bar_width}] --.--%",
                end="",
                flush=True,
            )
        except Exception as e:
            # Catch any other unexpected errors and display a fallback
            print(
                f"\r{self._message}: Error displaying progress: {str(e)}",
                end="",
                flush=True,
            )

    @contextmanager
    def progress_tracking(self, total: int, message: str) -> ContextManager[None]:
        """Context manager for automatic progress tracking.

        This method allows for using the ProgressDisplay in a with statement,
        automatically handling start and completion.

        Args:
            total (int): Total number of steps for the operation.
            message (str): Message to display with the progress bar.

        Yields:
            None

        Example:
            ```python
            progress = ProgressDisplay()
            with progress.progress_tracking(10, "Processing files"):
                for i in range(10):
                    # do work
                    progress.advance()
            ```
        """
        try:
            self.start(total, message)
            yield
        except Exception as e:
            # Print error information but still ensure we complete the progress
            print(
                f"\n{Fore.RED}Error during progress tracking: {str(e)}{Style.RESET_ALL}",
                file=sys.stderr,
            )
            raise
        finally:
            # Ensure progress is completed even if an exception occurs
            if self._active:
                self.complete()

    def __enter__(self) -> "ProgressDisplay":
        """Enter method for using ProgressDisplay as a context manager.

        Returns:
            ProgressDisplay: Returns self for use in context manager.

        Note:
            This requires calling start() separately before or inside the with block.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit method for using ProgressDisplay as a context manager.

        Args:
            exc_type: Exception type if an exception was raised, otherwise None
            exc_val: Exception value if an exception was raised, otherwise None
            exc_tb: Exception traceback if an exception was raised, otherwise None

        Note:
            This will call complete() if progress is active.
        """
        if self._active:
            self.complete()


def print_ascii_banner_with_stars(banner_text: str = "AGENTRADIS") -> None:
    """Print a large ASCII art banner surrounded by stars with double border."""
    # Extra large ASCII art
    ascii_art = [
        "    _____    _______ ______ _   _ _______ _____            _____ _____ _____ ",
        "   /  _  \\  |  _____|  ____| \\ | |__   __|  __ \\    /\\   |  __ \\_   _/ ____|",
        "  | |_| |   | |  __ | |__  |  \\| |  | |  | |__) |  /  \\  | |  | || || (___  ",
        "  |  _  /   | | |_ ||  __| | . ` |  | |  |  _  /  / /\\ \\ | |  | || | \\___ \\ ",
        "  | | \\ \\   | |__| || |____| |\\  |  | |  | | \\ \\ / ____ \\| |__| || |_____) |",
        "  |_|  \\_\\  |______|______|_| \\_|  |_|  |_|  \\_/_/    \\_\\_____/_____|____/ ",
    ]

    # Calculate banner dimensions
    banner_width = max(len(line) for line in ascii_art) + 8  # Extra padding

    # Print top stars
    print("\n" + "✧ " * (banner_width // 2))

    # Print top box border with stars
    print(f"{Fore.YELLOW}╔{'═' * (banner_width + 4)}╗{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}║{' ' * (banner_width + 4)}║{Style.RESET_ALL}")

    # Print ASCII art centered
    for line in ascii_art:
        padding = (banner_width - len(line)) // 2
        print(
            f"{Fore.YELLOW}║  {' ' * padding}{Fore.CYAN}{line}{' ' * (banner_width - len(line) - padding)}  {Fore.YELLOW}║{Style.RESET_ALL}"
        )

    # Print bottom box with stars
    print(f"{Fore.YELLOW}║{' ' * (banner_width + 4)}║{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}╚{'═' * (banner_width + 4)}╝{Style.RESET_ALL}")

    # Print bottom stars
    print("✧ " * (banner_width // 2) + "\n")


def display_system_introduction() -> None:
    """Display the system introduction and available tools."""
    console = Console()

    # System overview between stars
    print("✧ " * 30)
    console.print(
        "\n[bold blue]Welcome to AGENTRADIS - Advanced General-purpose ENhanced Task-driven Radis Assistant[/bold blue]"
    )
    console.print(
        "\nAGENTRADIS is an intelligent system designed to help you with various software development and automation tasks."
    )
    console.print(
        "It combines advanced planning capabilities with a suite of specialized tools to assist you effectively.\n"
    )
    print("✧ " * 30 + "\n")

    # Available tools section in magenta double-bordered box
    tools_panel = Panel(
        "\n".join(
            [
                "  \U0001f50d Code Analysis - Examine and understand your codebase",
                "  \U0001f4dd Code Generation - Create new code based on your requirements",
                "  \U0001f527 Refactoring - Improve existing code structure",
                "  \U0001f528 Build & Test - Compile and test your applications",
                "  \U0001f4ca Documentation - Generate and update documentation",
                "  \U0001f680 Deployment - Help with deployment tasks",
                "  \U0001f4a1 Problem Solving - Assist with debugging and problem resolution",
            ]
        ),
        title="[bold]Available Tools[/bold]",
        border_style="magenta",
        box=rich.box.DOUBLE,
        padding=(1, 2),
    )
    console.print(tools_panel)

    # Bottom message
    console.print("\n[italic]Type your request or question to begin...[/italic]\n")
    console.print("=" * shutil.get_terminal_size().columns + "\n")


def print_response_box(title: str = "Response:", content: str = "") -> None:
    """Print a response in a double-bordered box with title."""
    console = Console()

    # Get terminal width
    term_width = shutil.get_terminal_size().columns
    box_width = min(term_width - 4, 100)  # Max width of 100 chars

    # Create the title box (smaller width)
    title_width = len(title) + 4
    title_padding = (box_width - title_width) // 2
    title_box = (
        f"{Fore.CYAN}╔{'═' * title_width}╗\n"
        f"║ {Fore.WHITE}{title}{Fore.CYAN} ║\n"
        f"╚{'═' * title_width}╝{Style.RESET_ALL}"
    )

    # Create the main content box
    print("\n" + "═" * box_width)  # Top separator

    # Print centered title box
    print(" " * title_padding + title_box)

    # Create main content box
    print(f"{Fore.BLUE}╔{'═' * box_width}╗{Style.RESET_ALL}")

    # Word wrap and print content
    # First, add speaker prefix based on role
    if title.lower() == "you:":
        content = f"{Fore.GREEN}You:{Style.RESET_ALL} {content}"
    elif not content.startswith("Assistant:"):
        content = f"{Fore.CYAN}Assistant:{Style.RESET_ALL} {content}"

    # Process content line by line with word wrap
    from textwrap import wrap

    for paragraph in content.split("\n"):
        # Word wrap each paragraph
        for line in wrap(paragraph, width=box_width - 4):  # -4 for padding
            print(
                f"{Fore.BLUE}║{Style.RESET_ALL}  {line}{' ' * (box_width-2-len(line))}{Fore.BLUE}║{Style.RESET_ALL}"
            )

    # Bottom border
    print(f"{Fore.BLUE}╚{'═' * box_width}╝{Style.RESET_ALL}")
    print(" " * title_padding + "═" * box_width)  # Bottom separator


def setup_display(
    debug: bool = False, color: bool = True, timestamps: bool = True
) -> tuple[ToolDisplay, ArtifactDisplay]:
    """Initialize and configure all display components."""
    config = DisplayConfig(
        debug_mode=debug, color_output=color, show_timestamps=timestamps
    )
    tool_display = ToolDisplay(config)
    artifact_display = ArtifactDisplay(config)
    return (tool_display, artifact_display)


class InfoDisplay:
    def __init__(self, config: Optional[DisplayConfig] = None):
        self.config = config or DisplayConfig()
        self.console = Console()

    def info(self, message: str):
        """Display an informational message with appropriate formatting"""
        color = "blue" if self.config.color_output else "white"
        panel = Panel(message, title="ℹ️ Info", border_style=color, padding=(1, 2))
        self.console.print(panel)
        # Add separator after info message
        self.console.print("=" * self.console.width, style="dim")

    def success(self, message: str):
        """Display a success message with appropriate formatting"""
        color = "green" if self.config.color_output else "white"
        panel = Panel(message, title="✅ Success", border_style=color, padding=(1, 2))
        self.console.print(panel)
        # Add separator after success message
        self.console.print("=" * self.console.width, style="dim")

    def error(self, message: str):
        """Display an error message with appropriate formatting"""
        color = "red" if self.config.color_output else "white"
        panel = Panel(message, title="❌ Error", border_style=color, padding=(1, 2))
        self.console.print(panel)
        # Add separator after error message
        self.console.print("=" * self.console.width, style="dim")

    def clear(self):
        """Clear the console display"""
        self.console.clear()
