#!/usr/bin/env python3
import click
import json
import asyncio
from datetime import datetime
from typing import Optional
from app.agent.radis import RadisAgent, DiagnosticInfo
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()


def format_timestamp(ts: float) -> str:
    """Format a timestamp into a readable string."""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def create_error_table(errors: list) -> Table:
    """Create a rich table for error display."""
    table = Table(title="Errors")
    table.add_column("Time", style="cyan")
    table.add_column("Type", style="red")
    table.add_column("Message", style="yellow")
    table.add_column("Context", style="blue")

    for error in errors:
        table.add_row(
            format_timestamp(error["timestamp"]),
            error["type"],
            error["message"],
            json.dumps(error["context"], indent=2),
        )
    return table


def create_state_table(states: list) -> Table:
    """Create a rich table for state transitions."""
    table = Table(title="State Transitions")
    table.add_column("Time", style="cyan")
    table.add_column("State", style="green")
    table.add_column("Context", style="blue")

    for state in states:
        table.add_row(
            format_timestamp(state["timestamp"]),
            state["state"],
            json.dumps(state["context"], indent=2),
        )
    return table


async def initialize_agent() -> RadisAgent:
    """Initialize and configure a RadisAgent."""
    agent = RadisAgent(model="gpt-4")
    await agent.async_setup()
    return agent


async def cleanup_agent(agent: RadisAgent):
    """Cleanup agent resources."""
    if agent:
        await agent.cleanup()


def run_async(coro):
    """Run an async function in the event loop."""
    return asyncio.get_event_loop().run_until_complete(coro)


@click.group()
def cli():
    """Radis Diagnostic Tool"""
    pass


@cli.command()
@click.argument("agent_id", required=False)
def show(agent_id: Optional[str] = None):
    """Display diagnostic information for a Radis agent."""

    async def _show():
        agent = None
        try:
            agent = await initialize_agent()

            # Get diagnostic report
            report = await agent.get_diagnostic_report()

            # Display errors
            if report.get("errors"):
                console.print(create_error_table(report["errors"]))
            else:
                console.print("[green]No errors recorded[/green]")

            # Display state transitions
            if report.get("runtime_states"):
                console.print("\n")
                console.print(create_state_table(report["runtime_states"]))

            # Display LLM info
            if report.get("last_llm_request"):
                console.print("\n[bold]Last LLM Request:[/bold]")
                rprint(report["last_llm_request"])

            # Display tool execution info
            if report.get("last_tool_execution"):
                console.print("\n[bold]Last Tool Execution:[/bold]")
                rprint(report["last_tool_execution"])

            # Display memory stats
            if report.get("memory_stats"):
                console.print("\n[bold]Memory Stats:[/bold]")
                rprint(report["memory_stats"])

            # Display tool stats
            if report.get("tool_stats"):
                console.print("\n[bold]Tool Stats:[/bold]")
                rprint(report["tool_stats"])

        except Exception as e:
            console.print(f"[red]Error getting diagnostic information: {str(e)}[/red]")
        finally:
            if agent:
                await cleanup_agent(agent)

    run_async(_show())


@cli.command()
def clear():
    """Clear diagnostic information."""

    async def _clear():
        agent = None
        try:
            agent = await initialize_agent()
            agent.diagnostic_info = DiagnosticInfo()
            console.print("[green]Diagnostic information cleared successfully[/green]")
        except Exception as e:
            console.print(f"[red]Error clearing diagnostic information: {str(e)}[/red]")
        finally:
            if agent:
                await cleanup_agent(agent)

    run_async(_clear())


if __name__ == "__main__":
    cli()
