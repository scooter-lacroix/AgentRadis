from typing import Any, Optional
import threading
import time
import sys
from colorama import Fore, Style, init

init(autoreset=True)


class ToolDisplay:
    def __init__(self):
        self.current_tool = None

    def set_tool(self, tool_name: str) -> None:
        self.current_tool = tool_name
        print(f"{Fore.CYAN}Using tool: {tool_name}{Style.RESET_ALL}")

    def show_result(self, result: Any) -> None:
        print(f"{Fore.GREEN}Tool result: {result}{Style.RESET_ALL}")

    @staticmethod
    def show_tool_call(name: str, args: Any) -> None:
        """Display tool call information."""
        print(f"{Fore.CYAN}Using tool: {name}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Arguments: {args}{Style.RESET_ALL}")

    @staticmethod
    def show_tool_result(result: Any, success: bool = True) -> None:
        """Display tool result with appropriate styling."""
        if success:
            print(f"{Fore.GREEN}Tool result: {result}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Tool error: {result}{Style.RESET_ALL}")


class ArtifactDisplay:
    def show_artifact(self, artifact_type: str, content: Any) -> None:
        print(f"{Fore.YELLOW}[{artifact_type}]{Style.RESET_ALL}")
        print(f"{content}\n")

    def code_preview(self, content: str, language: str = "python") -> None:
        """Display code with syntax highlighting indicators."""
        print(f"{Fore.YELLOW}```{language}{Style.RESET_ALL}")
        print(content)
        print(f"{Fore.YELLOW}```{Style.RESET_ALL}")

    def web_preview(self, content: str) -> None:
        """Display web content preview."""
        print(f"{Fore.BLUE}Web Content Preview:{Style.RESET_ALL}")
        print(content)

    def project_structure(self, structure: str) -> None:
        """Display project structure in a tree-like format."""
        print(f"{Fore.GREEN}Project Structure:{Style.RESET_ALL}")
        print(structure)


class ProgressDisplay:
    def __init__(self):
        self.current_step = 0
        self.total_steps = 0
        self._thinking = False
        self._thinking_thread = None

    def start_progress(self, total: int) -> None:
        self.current_step = 0
        self.total_steps = total
        print(f"{Fore.BLUE}Starting process (0/{total}){Style.RESET_ALL}")

    def update_progress(self, step: int, message: Optional[str] = None) -> None:
        self.current_step = step
        status = f"Progress: {step}/{self.total_steps}"
        if message:
            status += f" - {message}"
        print(f"{Fore.BLUE}{status}{Style.RESET_ALL}")

    def show_thinking(self) -> None:
        """Start displaying an animated 'Thinking...' indicator."""
        self._thinking = True
        self._thinking_thread = threading.Thread(target=self._animate_thinking)
        self._thinking_thread.daemon = True
        self._thinking_thread.start()

    def stop_thinking(self) -> None:
        """Stop the thinking animation."""
        self._thinking = False
        if self._thinking_thread:
            self._thinking_thread.join(timeout=1.0)  # Wait for thread to finish
            # Clear the line
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()

    def _animate_thinking(self) -> None:
        """Animate the thinking process with spinner."""
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        while self._thinking:
            frame = frames[i % len(frames)]
            sys.stdout.write(f"\r{Fore.CYAN}[{frame}] Thinking...{Style.RESET_ALL}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1


def setup_display() -> tuple[ToolDisplay, ArtifactDisplay, ProgressDisplay]:
    return ToolDisplay(), ArtifactDisplay(), ProgressDisplay()
