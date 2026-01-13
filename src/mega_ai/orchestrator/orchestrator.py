"""Main orchestrator class with agentic loop."""

import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from mega_ai.orchestrator.exceptions import (
    AIProviderError,
    MaxIterationsError,
    OrchestratorError,
)
from mega_ai.orchestrator.models import ProjectInfo, TaskConfig, TaskStatus, ToolResult
from mega_ai.orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT, create_user_prompt
from mega_ai.orchestrator.task_manager import (
    create_task_folder,
    generate_task_uuid,
    save_task_config,
    update_task_status,
)
from mega_ai.orchestrator.tools import ORCHESTRATOR_TOOLS, ToolHandler
from mega_ai.providers.base import AIResponse, BaseProvider, Message, ToolCall


class Orchestrator:
    """
    Main orchestrator class that runs the agentic analysis and script generation loop.
    """

    MAX_ITERATIONS = 50  # Safety limit for agentic loop

    def __init__(
        self,
        provider: BaseProvider,
        console: Console | None = None,
    ):
        self.provider = provider
        self.console = console or Console()
        self.logger = logging.getLogger(__name__)

    def run(self, task_description: str, project_path: Path | None = None) -> str:
        """
        Run the orchestrator to analyze a project and generate scripts.

        Args:
            task_description: User's description of the transformation task
            project_path: Path to the project (defaults to current directory)

        Returns:
            The task UUID

        Raises:
            OrchestratorError: On various failure conditions
        """
        project_path = project_path or Path.cwd()
        project_path = project_path.resolve()

        # Generate task UUID and create folder
        task_uuid = generate_task_uuid()
        task_path = create_task_folder(project_path, task_uuid)

        self.console.print(
            Panel.fit(
                f"[bold blue]MEGA-AI Orchestrator[/bold blue]\n"
                f"Task: {task_description}\n"
                f"UUID: {task_uuid}",
                border_style="blue",
            )
        )

        # Initialize task config
        config = TaskConfig(
            uuid=task_uuid,
            description=task_description,
            status=TaskStatus.ANALYZING,
            project=ProjectInfo(path=project_path),
            models={
                "orchestrator": self.provider.get_model_name("orchestrator"),
                "worker": self.provider.get_model_name("worker"),
            },
        )
        save_task_config(task_path, config)

        # Setup logging to file
        self._setup_file_logging(task_path)

        # Initialize tool handler
        tool_handler = ToolHandler(
            project_path=project_path,
            task_path=task_path,
            console=self.console,
        )

        # Initialize conversation
        messages: list[Message] = [
            Message(
                role="user",
                content=create_user_prompt(task_description, str(project_path)),
            )
        ]

        self.console.print("\n[bold cyan]Analyzing project...[/bold cyan]")

        try:
            # Run agentic loop
            iteration = 0
            while iteration < self.MAX_ITERATIONS:
                iteration += 1
                self.logger.info(f"Iteration {iteration}")

                # Call AI
                response = self._call_ai(messages)

                # Log AI response
                if response.content:
                    self.logger.info(f"AI response: {response.content[:500]}...")
                    self.console.print(f"\n[dim]{response.content}[/dim]")

                # Check if AI wants to call tools
                if response.tool_calls:
                    # Process each tool call
                    tool_results: list[tuple[ToolCall, ToolResult]] = []
                    for tool_call in response.tool_calls:
                        self.logger.info(
                            f"Tool call: {tool_call.name}({tool_call.arguments})"
                        )

                        # Show tool call to user
                        self._print_tool_call(tool_call)

                        result = tool_handler.handle_tool_call(
                            tool_call.name, tool_call.arguments
                        )
                        tool_results.append((tool_call, result))

                        # Show tool result to user
                        self._print_tool_result(tool_call, result)

                        if result.output:
                            self.logger.info(f"Tool result: {result.output[:500]}...")
                        if result.error:
                            self.logger.warning(f"Tool error: {result.error}")

                    # Build tool results message for next turn
                    tool_results_content = self._format_tool_results(tool_results)

                    # Add assistant's response with tool use marker
                    assistant_content = response.content or ""
                    for tool_call in response.tool_calls:
                        assistant_content += f"\n[Called {tool_call.name}]"
                    messages.append(Message(role="assistant", content=assistant_content))

                    # Add tool results as user message
                    messages.append(Message(role="user", content=tool_results_content))

                    # Check if task completed
                    if tool_handler.task_completed:
                        break

                else:
                    # No tool calls - AI might be done or confused
                    if response.content:
                        messages.append(
                            Message(role="assistant", content=response.content)
                        )

                    # Check if AI wrote "[Called tool]" in text instead of actual tool call
                    if response.content and "[Called " in response.content:
                        self.console.print(
                            "[yellow]AI simulated tool call in text. Prompting to use actual tool...[/yellow]"
                        )
                        messages.append(
                            Message(
                                role="user",
                                content=(
                                    "You wrote '[Called ...]' in your text response, but this does NOT execute the tool. "
                                    "You MUST use the actual tool_use format to call tools. "
                                    "Please call the write_file tool properly to write the file."
                                ),
                            )
                        )
                    # Check stop reason
                    elif response.stop_reason in ("end_turn", "stop"):
                        # AI finished without calling complete_task
                        self.console.print(
                            "[yellow]AI finished without calling complete_task. Prompting...[/yellow]"
                        )
                        messages.append(
                            Message(
                                role="user",
                                content=(
                                    "Have you finished generating all scripts? "
                                    "If so, please call the complete_task tool with a summary."
                                ),
                            )
                        )
                    else:
                        break

            else:
                # Loop didn't break - max iterations reached
                raise MaxIterationsError(
                    f"Orchestrator exceeded {self.MAX_ITERATIONS} iterations"
                )

            # Task completed successfully
            update_task_status(task_path, TaskStatus.READY)

            self.console.print("\n[bold green]Task ready![/bold green]")
            if tool_handler.completion_summary:
                self.console.print(f"\n{tool_handler.completion_summary}")

            self.console.print("\n[bold]Next steps:[/bold]")
            self.console.print(
                f"  Preview (dry-run): [cyan]mega-ai worker {task_uuid} --dry-run[/cyan]"
            )
            self.console.print(f"  Execute: [cyan]mega-ai worker {task_uuid}[/cyan]")

            return task_uuid

        except Exception as e:
            # Update status to failed
            import contextlib

            with contextlib.suppress(Exception):
                update_task_status(task_path, TaskStatus.FAILED)
            self.logger.exception("Orchestrator failed")
            if isinstance(e, OrchestratorError):
                raise
            raise OrchestratorError(f"Orchestrator failed: {e}") from e

    def _call_ai(self, messages: list[Message]) -> AIResponse:
        """Call the AI provider with current messages."""
        try:
            return self.provider.chat(
                messages=messages,
                system=ORCHESTRATOR_SYSTEM_PROMPT,
                tools=ORCHESTRATOR_TOOLS,
                max_tokens=4096,
                model_type="orchestrator",
            )
        except Exception as e:
            raise AIProviderError(f"AI provider error: {e}") from e

    def _print_tool_call(self, tool_call: ToolCall) -> None:
        """Print tool call information to console."""
        if tool_call.name == "run_command":
            cmd = tool_call.arguments.get("command", "")
            self.console.print(f"\n[cyan]$ {cmd}[/cyan]")
        elif tool_call.name == "write_file":
            path = tool_call.arguments.get("path") or tool_call.arguments.get("file_path", "")
            self.console.print(f"\n[cyan]Writing file:[/cyan] {path}")
        elif tool_call.name == "ask_user":
            self.console.print("\n[cyan]Asking user...[/cyan]")
        elif tool_call.name == "complete_task":
            self.console.print("\n[cyan]Completing task...[/cyan]")
        else:
            self.console.print(f"\n[cyan]Calling {tool_call.name}...[/cyan]")

    def _print_tool_result(self, tool_call: ToolCall, result: ToolResult) -> None:
        """Print tool result to console."""
        if tool_call.name == "run_command":
            if result.success and result.output:
                # Truncate long outputs for display
                output = result.output
                lines = output.split("\n")
                if len(lines) > 20:
                    output = "\n".join(lines[:20]) + f"\n... ({len(lines) - 20} more lines)"
                self.console.print(f"[dim]{output}[/dim]")
            elif result.error:
                self.console.print(f"[red]{result.error}[/red]")
        elif tool_call.name == "write_file":
            if result.success:
                self.console.print(f"[green]  ✓ {result.output}[/green]")
            else:
                self.console.print(f"[red]  ✗ {result.error}[/red]")
        elif result.error:
            self.console.print(f"[red]{result.error}[/red]")

    def _format_tool_results(
        self, tool_results: list[tuple[ToolCall, ToolResult]]
    ) -> str:
        """Format tool results as a message for the AI."""
        parts = []
        for tool_call, result in tool_results:
            if result.success:
                parts.append(f"Tool `{tool_call.name}` result:\n{result.output}")
            else:
                parts.append(f"Tool `{tool_call.name}` error:\n{result.error}")
        return "\n\n".join(parts)

    def _setup_file_logging(self, task_path: Path) -> None:
        """Setup logging to file in task folder."""
        log_file = task_path / "logs" / "orchestrator.log"
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
