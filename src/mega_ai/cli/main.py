"""Main CLI entry point for MEGA-AI."""

import typer
from rich.console import Console

from mega_ai import __version__

app = typer.Typer(
    name="mega-ai",
    help="AI-powered data transformation tool",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold blue]MEGA-AI[/bold blue] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """MEGA-AI - AI-powered data transformation tool."""
    pass


@app.command()
def init() -> None:
    """Initialize MEGA-AI configuration."""
    from mega_ai.cli.commands.init import run_init

    run_init()


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description for the AI to execute"),
) -> None:
    """Run Orchestrator AI to analyze and generate transformation scripts."""
    console.print(f"[bold]Task:[/bold] {task}")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def worker(
    uuid: str = typer.Argument(..., help="Task UUID to execute"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without executing"),
) -> None:
    """Execute Worker AI for a specific task."""
    console.print(f"[bold]Task UUID:[/bold] {uuid}")
    console.print(f"[bold]Dry run:[/bold] {dry_run}")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def rollback(
    uuid: str = typer.Argument(..., help="Task UUID to rollback"),
) -> None:
    """Rollback changes for a specific task."""
    console.print(f"[bold]Rolling back:[/bold] {uuid}")
    console.print("[yellow]Not implemented yet[/yellow]")


@app.command()
def history() -> None:
    """Show task history."""
    console.print("[yellow]Not implemented yet[/yellow]")


if __name__ == "__main__":
    app()
