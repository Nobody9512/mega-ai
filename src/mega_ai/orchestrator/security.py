"""Security module for command validation."""

import re
import shlex
from typing import NamedTuple


class CommandValidation(NamedTuple):
    """Result of command validation."""

    is_safe: bool
    reason: str | None = None


# Commands that are explicitly blocked
BLOCKED_COMMANDS = {
    # Destructive shell commands
    "rm",
    "rmdir",
    "unlink",
    "shred",
    "mv",  # Could overwrite files
    "dd",  # Dangerous disk operations
    # Write operations
    "touch",
    "mkdir",
    "tee",
    "cp",  # Could overwrite
    # Permission/ownership
    "chmod",
    "chown",
    "chgrp",
    # System commands
    "sudo",
    "su",
    "kill",
    "killall",
    "pkill",
    "shutdown",
    "reboot",
    "halt",
    # Network
    "curl",
    "wget",  # Could download malicious content
}

# SQL/DB destructive keywords (checked in arguments)
BLOCKED_SQL_KEYWORDS = {
    "drop",
    "delete",
    "truncate",
    "update",
    "insert",
    "alter",
    "create",
    "grant",
    "revoke",
}

# Patterns that indicate dangerous operations
DANGEROUS_PATTERNS = [
    r">\s*\S+",  # Output redirection: > file
    r">>\s*\S+",  # Append redirection: >> file
    r"\|\s*tee\b",  # Pipe to tee
    r";\s*rm\b",  # Chained rm command
    r"&&\s*rm\b",  # Chained rm command
    r"\$\(",  # Command substitution
    r"`",  # Backtick command substitution
    r"eval\s",  # Eval command
    r"exec\s",  # Exec command
]

# Safe commands that are explicitly allowed
SAFE_COMMANDS = {
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    "file",
    "stat",
    "du",
    "df",
    "pwd",
    "echo",
    "env",
    "printenv",
    "which",
    "whereis",
    "type",
    "git",
    "php",
    "python",
    "python3",
    "node",
    "npm",
    "npx",
    "yarn",
    "pnpm",
    "composer",
    "artisan",
    "psql",
    "mysql",
    "mongo",
    "mongosh",
    "redis-cli",
    "sqlite3",
    "tree",
    "less",
    "more",
    "sort",
    "uniq",
    "cut",
    "awk",
    "sed",  # sed is read-only when used without -i
    "jq",
    "yq",
    "realpath",
    "dirname",
    "basename",
}


def validate_command(command: str) -> CommandValidation:
    """
    Validate that a command is safe to execute (read-only).

    Returns CommandValidation with is_safe=True if command is allowed.
    """
    command = command.strip()

    if not command:
        return CommandValidation(False, "Empty command")

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return CommandValidation(False, f"Dangerous pattern detected: {pattern}")

    try:
        # Parse command to get tokens
        tokens = shlex.split(command)
        if not tokens:
            return CommandValidation(False, "Could not parse command")

        base_cmd = tokens[0].split("/")[-1]  # Handle full paths

        # Check if command is blocked
        if base_cmd.lower() in BLOCKED_COMMANDS:
            return CommandValidation(False, f"Blocked command: {base_cmd}")

        # Check for sed -i (in-place editing)
        if base_cmd == "sed" and "-i" in tokens:
            return CommandValidation(False, "sed with -i flag is not allowed")

        # Check arguments for dangerous SQL keywords (for DB CLI tools)
        if base_cmd in ("mysql", "psql", "mongo", "mongosh", "sqlite3"):
            args_str = " ".join(tokens[1:]).lower()
            for keyword in BLOCKED_SQL_KEYWORDS:
                # Look for keyword followed by space or end of string
                if re.search(rf"\b{keyword}\b", args_str):
                    return CommandValidation(
                        False, f"SQL keyword not allowed: {keyword}"
                    )

    except ValueError as e:
        return CommandValidation(False, f"Command parse error: {e}")

    return CommandValidation(True)
