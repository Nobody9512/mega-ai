# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MEGA-AI is an AI-powered data transformation tool that automates repetitive integration work. It uses a two-stage architecture:

1. **Orchestrator** (Smart Model - Claude Opus/GPT-4o): Analyzes codebase, detects framework/database, generates transformation scripts
2. **Worker** (Fast Model - Claude Sonnet/GPT-4o-mini): Executes generated scripts with backups and rollback support

## Build & Development Commands

# before run python code use this command
source .venv/bin/activate

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run tests with coverage
pytest --cov

# Lint
ruff check src/

# Format
ruff format src/

# Type checking
mypy src/
```

## CLI Commands

```bash
mega-ai init              # Setup configuration (API keys, model selection)
mega-ai run "<task>"      # Orchestrator: analyze & generate scripts
mega-ai worker <uuid>     # Worker: execute generated scripts (stub)
mega-ai rollback <uuid>   # Restore from backup (stub)
mega-ai history           # Show past tasks (stub)
```

## Architecture

```
src/mega_ai/
├── cli/                  # Typer CLI (main.py, commands/)
├── orchestrator/         # Core agentic loop
│   ├── orchestrator.py   # Main Orchestrator class (max 50 iterations)
│   ├── tools.py          # 4 tools: run_command, write_file, ask_user, complete_task
│   ├── prompts.py        # System prompt & user prompt templates
│   ├── models.py         # Pydantic models (TaskConfig, ProjectInfo, etc)
│   ├── task_manager.py   # Task folder & config management
│   └── security.py       # Command validation (blocklist/safelist)
├── providers/            # AI provider abstractions
│   ├── base.py           # Abstract BaseProvider
│   ├── anthropic.py      # Claude implementation
│   └── openai.py         # GPT implementation
├── utils/config.py       # YAML config management (~/.mega-ai/config.yaml)
├── analyzers/            # Placeholder for framework analyzers
└── worker/               # Placeholder for worker AI
```

Task data stored in `.mega-ai/tasks/{uuid}/` with config.json, backup.py, runner.py, backups/, logs/.

## Key Patterns

- **Agentic Loop**: Orchestrator iterates with tool calls until `complete_task` is signaled
- **Provider Abstraction**: `BaseProvider` interface allows swapping AI backends
- **Pydantic Models**: All data structures validated via Pydantic
- **Rich Console**: User output uses Rich library
- **Path Handling**: Uses `pathlib.Path` exclusively
- **Security**: Command blocklist prevents destructive operations; 30-second timeout per command

## Adding New Components

**New CLI command**: Add to `src/mega_ai/cli/main.py` with `@app.command()` decorator

**New Orchestrator tool**:
1. Add to `ORCHESTRATOR_TOOLS` in `tools.py`
2. Add handler method to `ToolHandler` class
3. Update system prompt in `prompts.py`

**New AI provider**:
1. Create class extending `BaseProvider` in `providers/`
2. Implement `chat()` and `get_model_name()` methods
3. Update config handling in `utils/config.py` and init command

## Code Style

- Python 3.10+
- Line length: 100 characters
- Ruff for linting (E, F, W, I, UP, B, C4, SIM rules)
- Strict mypy with ignore_missing_imports
