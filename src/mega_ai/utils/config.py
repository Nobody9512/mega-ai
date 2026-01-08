"""Configuration management for MEGA-AI."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """Configuration for an AI provider."""

    api_key: str = ""


class ProvidersConfig(BaseModel):
    """All provider configurations."""

    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)


class ModelsConfig(BaseModel):
    """Model configurations."""

    orchestrator: str = "claude-opus-4-5-20251101"
    worker: str = "claude-sonnet-4-5-20250929"
    default_provider: str = "anthropic"


class Config(BaseModel):
    """Main MEGA-AI configuration."""

    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)


def get_config_dir() -> Path:
    """Get the MEGA-AI config directory path."""
    return Path.home() / ".mega-ai"


def get_config_path() -> Path:
    """Get the config file path."""
    return get_config_dir() / "config.yaml"


def ensure_config_dir() -> Path:
    """Ensure config directory exists with proper permissions."""
    config_dir = get_config_dir()
    config_dir.mkdir(mode=0o700, exist_ok=True)
    return config_dir


def load_config() -> Config:
    """Load configuration from file."""
    config_path = get_config_path()

    if not config_path.exists():
        return Config()

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    return Config(**data)


def save_config(config: Config) -> None:
    """Save configuration to file."""
    ensure_config_dir()
    config_path = get_config_path()

    # Convert to dict, excluding None values
    data = config.model_dump(exclude_none=True)

    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    # Set secure permissions (owner read/write only)
    os.chmod(config_path, 0o600)


def get_provider(config: Config | None = None):
    """Get the configured AI provider instance."""
    if config is None:
        config = load_config()

    provider_name = config.models.default_provider

    if provider_name == "anthropic":
        from mega_ai.providers.anthropic import AnthropicProvider

        api_key = config.providers.anthropic.api_key
        if not api_key:
            raise ValueError("Anthropic API key not configured. Run 'mega-ai init' first.")

        return AnthropicProvider(
            api_key=api_key,
            orchestrator_model=config.models.orchestrator,
            worker_model=config.models.worker,
        )

    elif provider_name == "openai":
        from mega_ai.providers.openai import OpenAIProvider

        api_key = config.providers.openai.api_key
        if not api_key:
            raise ValueError("OpenAI API key not configured. Run 'mega-ai init' first.")

        return OpenAIProvider(
            api_key=api_key,
            orchestrator_model=config.models.orchestrator,
            worker_model=config.models.worker,
        )

    else:
        raise ValueError(f"Unknown provider: {provider_name}")
