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
    from pathlib import Path

    from mega_ai.orchestrator import Orchestrator, OrchestratorError
    from mega_ai.utils.config import get_provider, load_config

    try:
        # Load config and get provider
        config = load_config()
        provider = get_provider(config)

        # Create orchestrator and run
        orchestrator = Orchestrator(provider=provider, console=console)
        orchestrator.run(task_description=task, project_path=Path.cwd())

    except ValueError as e:
        # Configuration errors
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print("Run [cyan]mega-ai init[/cyan] to configure.")
        raise typer.Exit(1) from None

    except OrchestratorError as e:
        console.print(f"[red]Orchestrator error:[/red] {e}")
        raise typer.Exit(1) from None

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(130) from None


@app.command()
def worker(
    uuid: str = typer.Argument(..., help="Task UUID to execute"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Preview changes without executing"
    ),
) -> None:
    """Execute Worker AI for a specific task."""
    from pathlib import Path

    from mega_ai.worker import Worker, WorkerError

    try:
        w = Worker(project_path=Path.cwd(), console=console)
        w.execute(task_uuid=uuid, dry_run=dry_run)

    except WorkerError as e:
        console.print(f"[red]Worker error:[/red] {e}")
        raise typer.Exit(1) from None

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(130) from None


@app.command()
def rollback(
    uuid: str = typer.Argument(..., help="Task UUID to rollback"),
    backup_file: str = typer.Option(
        None, "--file", "-f", help="Specific backup file to restore"
    ),
) -> None:
    """Rollback changes for a specific task."""
    from pathlib import Path

    from mega_ai.worker import RollbackError, Worker

    try:
        w = Worker(project_path=Path.cwd(), console=console)
        w.rollback(task_uuid=uuid, backup_file=backup_file)

    except RollbackError as e:
        console.print(f"[red]Rollback error:[/red] {e}")
        raise typer.Exit(1) from None

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(130) from None


@app.command()
def history() -> None:
    """Show task history."""
    from pathlib import Path

    from rich.table import Table

    from mega_ai.orchestrator.task_manager import list_tasks

    tasks = list_tasks(Path.cwd())

    if not tasks:
        console.print("[dim]No tasks found. Run 'mega-ai run' to create a task.[/dim]")
        return

    # Create table
    table = Table(title="Task History", show_header=True, header_style="bold")
    table.add_column("UUID", style="cyan")
    table.add_column("Status")
    table.add_column("Description", max_width=50)
    table.add_column("Created")

    # Status color mapping
    status_colors = {
        "pending": "dim",
        "analyzing": "yellow",
        "generating": "yellow",
        "ready": "green",
        "backing_up": "blue",
        "executing": "blue",
        "completed": "bold green",
        "failed": "red",
        "rolled_back": "yellow",
    }

    for task in tasks:
        color = status_colors.get(task.status.value, "white")
        status_text = f"[{color}]{task.status.value}[/{color}]"

        # Format date
        created = task.created_at.strftime("%Y-%m-%d %H:%M")

        # Truncate description
        desc = task.description
        if len(desc) > 47:
            desc = desc[:47] + "..."

        table.add_row(task.uuid, status_text, desc, created)

    console.print(table)


if __name__ == "__main__":
    app()
