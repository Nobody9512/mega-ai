"""Init command - setup MEGA-AI configuration."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from mega_ai.utils.config import (
    Config,
    ModelsConfig,
    ProviderConfig,
    ProvidersConfig,
    get_config_path,
    load_config,
    save_config,
)

console = Console()

ANTHROPIC_MODELS = {
    "orchestrator": [
        ("claude-opus-4-20250514", "claude-opus-4-20250514 (recommended)"),
        ("claude-sonnet-4-20250514", "claude-sonnet-4-20250514"),
    ],
    "worker": [
        ("claude-sonnet-4-20250514", "claude-sonnet-4-20250514 (recommended)"),
        ("claude-haiku-3-5-20241022", "claude-haiku-3-5-20241022 (faster, cheaper)"),
    ],
}

OPENAI_MODELS = {
    "orchestrator": [
        ("gpt-4o", "gpt-4o (recommended)"),
        ("gpt-4-turbo", "gpt-4-turbo"),
    ],
    "worker": [
        ("gpt-4o-mini", "gpt-4o-mini (recommended)"),
        ("gpt-4o", "gpt-4o"),
    ],
}


def select_option(prompt: str, options: list[tuple[str, str]]) -> str:
    """Display options and get user selection."""
    console.print(f"\n[bold]{prompt}[/bold]")
    for i, (_, label) in enumerate(options, 1):
        console.print(f"  {i}. {label}")

    while True:
        choice = Prompt.ask(">", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            pass
        console.print("[red]Invalid selection, try again.[/red]")


def run_init() -> None:
    """Run the init command."""
    console.print(
        Panel.fit(
            "[bold blue]Welcome to MEGA-AI![/bold blue] [white]🚀[/white]",
            border_style="blue",
        )
    )

    # Check existing config
    existing_config = load_config()
    if existing_config.providers.anthropic.api_key or existing_config.providers.openai.api_key:
        console.print("\n[yellow]Existing configuration found.[/yellow]")
        overwrite = Prompt.ask("Overwrite?", choices=["y", "n"], default="n")
        if overwrite.lower() != "y":
            console.print("[dim]Configuration unchanged.[/dim]")
            raise typer.Exit()

    # Select provider
    provider_options = [
        ("anthropic", "Anthropic (Claude)"),
        ("openai", "OpenAI (GPT)"),
        ("both", "Both"),
    ]
    provider = select_option("Select AI provider:", provider_options)

    providers_config = ProvidersConfig()
    models_config = ModelsConfig()

    # Configure Anthropic
    if provider in ("anthropic", "both"):
        console.print("\n[bold cyan]Anthropic Configuration[/bold cyan]")
        api_key = Prompt.ask("Enter Anthropic API key", password=True)

        if not api_key.startswith("sk-ant-"):
            console.print("[yellow]Warning: API key doesn't look like Anthropic key[/yellow]")

        providers_config.anthropic = ProviderConfig(api_key=api_key)

        if provider == "anthropic":
            models_config.default_provider = "anthropic"
            models_config.orchestrator = select_option(
                "Select orchestrator model (for analysis & planning):",
                ANTHROPIC_MODELS["orchestrator"],
            )
            models_config.worker = select_option(
                "Select worker model (for data transformation):",
                ANTHROPIC_MODELS["worker"],
            )

    # Configure OpenAI
    if provider in ("openai", "both"):
        console.print("\n[bold green]OpenAI Configuration[/bold green]")
        api_key = Prompt.ask("Enter OpenAI API key", password=True)

        if not api_key.startswith("sk-"):
            console.print("[yellow]Warning: API key doesn't look like OpenAI key[/yellow]")

        providers_config.openai = ProviderConfig(api_key=api_key)

        if provider == "openai":
            models_config.default_provider = "openai"
            models_config.orchestrator = select_option(
                "Select orchestrator model (for analysis & planning):",
                OPENAI_MODELS["orchestrator"],
            )
            models_config.worker = select_option(
                "Select worker model (for data transformation):",
                OPENAI_MODELS["worker"],
            )

    # If both providers, ask for default
    if provider == "both":
        default_provider = select_option(
            "Select default provider:",
            [
                ("anthropic", "Anthropic (Claude) - recommended"),
                ("openai", "OpenAI (GPT)"),
            ],
        )
        models_config.default_provider = default_provider

        if default_provider == "anthropic":
            models_config.orchestrator = select_option(
                "Select orchestrator model:",
                ANTHROPIC_MODELS["orchestrator"],
            )
            models_config.worker = select_option(
                "Select worker model:",
                ANTHROPIC_MODELS["worker"],
            )
        else:
            models_config.orchestrator = select_option(
                "Select orchestrator model:",
                OPENAI_MODELS["orchestrator"],
            )
            models_config.worker = select_option(
                "Select worker model:",
                OPENAI_MODELS["worker"],
            )

    # Save configuration
    config = Config(providers=providers_config, models=models_config)
    save_config(config)

    config_path = get_config_path()
    console.print(f"\n[green]✅ Configuration saved to {config_path}[/green]")

    # Show summary
    console.print("\n[bold]Configuration summary:[/bold]")
    console.print(f"  Provider: {models_config.default_provider}")
    console.print(f"  Orchestrator: {models_config.orchestrator}")
    console.print(f"  Worker: {models_config.worker}")
