"""Tool definitions and handlers for orchestrator."""

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Prompt

from mega_ai.orchestrator.models import ToolResult
from mega_ai.orchestrator.security import validate_command

# Tool schemas for AI (OpenAI/Anthropic compatible format)
ORCHESTRATOR_TOOLS: list[dict[str, Any]] = [
    {
        "name": "run_command",
        "description": (
            "Execute a shell command in the project directory. "
            "Use for read-only operations: ls, cat, grep, find, head, tail, wc, git status, etc. "
            "NEVER use for destructive operations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file in the task folder. "
            "Path is relative to .mega-ai/tasks/{uuid}/"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "File path relative to task folder "
                        "(e.g., 'backup.py', 'runner.py', 'config.json')"
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "ask_user",
        "description": (
            "Ask the user for clarification when the task is ambiguous "
            "or multiple options are available"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of choices for the user",
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "complete_task",
        "description": (
            "Mark the task as complete and ready for worker execution. "
            "Call this when all scripts have been generated."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Summary of what was analyzed and generated",
                }
            },
            "required": ["summary"],
        },
    },
]


class ToolHandler:
    """Handles execution of orchestrator tools."""

    ALLOWED_EXTENSIONS = {".py", ".json", ".md", ".txt", ".yaml", ".yml"}

    def __init__(
        self,
        project_path: Path,
        task_path: Path,
        console: Console,
    ):
        self.project_path = project_path
        self.task_path = task_path
        self.console = console
        self.task_completed = False
        self.completion_summary: str | None = None

    def handle_tool_call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Route tool call to appropriate handler."""
        handlers: dict[str, Callable[..., ToolResult]] = {
            "run_command": self._handle_run_command,
            "write_file": self._handle_write_file,
            "ask_user": self._handle_ask_user,
            "complete_task": self._handle_complete_task,
        }

        handler = handlers.get(name)
        if not handler:
            return ToolResult(success=False, output="", error=f"Unknown tool: {name}")

        try:
            return handler(**arguments)
        except TypeError as e:
            # Handle missing or extra arguments gracefully
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid arguments for {name}: {e}. Got: {list(arguments.keys())}",
            )

    def _handle_run_command(self, command: str) -> ToolResult:
        """Execute a shell command with security validation."""
        # Validate command first
        validation = validate_command(command)
        if not validation.is_safe:
            return ToolResult(
                success=False, output="", error=f"Command blocked: {validation.reason}"
            )

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[STDERR]: {result.stderr}"

            # Truncate very long outputs
            if len(output) > 10000:
                output = output[:10000] + "\n... (truncated)"

            return ToolResult(
                success=result.returncode == 0,
                output=output,
                error=None if result.returncode == 0 else f"Exit code: {result.returncode}",
            )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Command timed out (30s)")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def _handle_write_file(
        self,
        path: str | None = None,
        content: str | None = None,
        # Alternative argument names AI might use
        file_path: str | None = None,
        file_content: str | None = None,
        filename: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Write content to a file in the task folder."""
        # Handle alternative argument names
        actual_path = path or file_path or filename
        actual_content = content or file_content or kwargs.get("text")

        if not actual_path:
            return ToolResult(
                success=False,
                output="",
                error="Missing 'path' argument for write_file",
            )
        if actual_content is None:
            return ToolResult(
                success=False,
                output="",
                error="Missing 'content' argument for write_file",
            )

        # Sanitize path - only allow filename, no subdirectories for security
        clean_path = Path(actual_path).name

        # Block config.json - it's managed by the orchestrator
        if clean_path == "config.json":
            return ToolResult(
                success=True,
                output="config.json is auto-managed. Skipped. Continue with other files.",
            )

        # Only allow specific file extensions
        if not any(clean_path.endswith(ext) for ext in self.ALLOWED_EXTENSIONS):
            return ToolResult(
                success=False,
                output="",
                error=f"File extension not allowed. Allowed: {self.ALLOWED_EXTENSIONS}",
            )

        target_file = self.task_path / clean_path

        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(actual_content)
            return ToolResult(success=True, output=f"File written: {clean_path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def _handle_ask_user(
        self, question: str, options: list[str] | None = None
    ) -> ToolResult:
        """Ask user for clarification."""
        self.console.print("\n[bold yellow]Question from AI:[/bold yellow]")
        self.console.print(f"   {question}")

        if options:
            for i, opt in enumerate(options, 1):
                self.console.print(f"   {i}. {opt}")

            while True:
                answer = Prompt.ask(">")
                # Handle number input
                try:
                    idx = int(answer) - 1
                    if 0 <= idx < len(options):
                        return ToolResult(success=True, output=options[idx])
                except ValueError:
                    pass
                # Accept text answer
                if answer.strip():
                    return ToolResult(success=True, output=answer.strip())
                self.console.print("[red]Please provide an answer[/red]")
        else:
            answer = Prompt.ask(">")
            return ToolResult(success=True, output=answer)

    def _handle_complete_task(self, summary: str) -> ToolResult:
        """Mark task as complete."""
        self.task_completed = True
        self.completion_summary = summary
        return ToolResult(success=True, output="Task marked as complete")
