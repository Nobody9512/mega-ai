"""Tests for command validation security module."""

import pytest

from mega_ai.orchestrator.security import validate_command


class TestDevNullRedirection:
    """Test /dev/null redirection handling."""

    def test_stderr_to_devnull_allowed(self):
        """stderr redirection to /dev/null should be allowed."""
        result = validate_command("find /path 2>/dev/null")
        assert result.is_safe, f"Should be safe: {result.reason}"

    def test_stdout_to_devnull_allowed(self):
        """stdout redirection to /dev/null should be allowed."""
        result = validate_command("command >/dev/null")
        assert result.is_safe, f"Should be safe: {result.reason}"

    def test_both_to_devnull_allowed(self):
        """Both stdout and stderr to /dev/null should be allowed."""
        result = validate_command("command >/dev/null 2>&1")
        assert result.is_safe, f"Should be safe: {result.reason}"

    def test_stderr_devnull_with_pipe_and_head(self):
        """Complex command with stderr to /dev/null and pipe should work."""
        result = validate_command("find /path -name '*.php' 2>/dev/null | head -5")
        assert result.is_safe, f"Should be safe: {result.reason}"

    def test_ls_with_devnull_and_head(self):
        """ls with stderr to /dev/null and head should work."""
        result = validate_command("ls -la /path 2>/dev/null | head -20")
        assert result.is_safe, f"Should be safe: {result.reason}"


class TestDangerousRedirection:
    """Test that dangerous redirections are blocked."""

    def test_stdout_to_file_blocked(self):
        """stdout redirection to a file should be blocked."""
        result = validate_command("echo test > /tmp/file")
        assert not result.is_safe

    def test_append_to_file_blocked(self):
        """Append redirection to a file should be blocked."""
        result = validate_command("cat x >> /tmp/file")
        assert not result.is_safe

    def test_redirect_to_home_blocked(self):
        """Redirection to home directory should be blocked."""
        result = validate_command("echo test > ~/file.txt")
        assert not result.is_safe


class TestSafeCommands:
    """Test that safe commands are allowed."""

    def test_simple_find(self):
        """Simple find command should be allowed."""
        result = validate_command("find /path -name '*.py'")
        assert result.is_safe

    def test_simple_ls(self):
        """Simple ls command should be allowed."""
        result = validate_command("ls -la /path")
        assert result.is_safe

    def test_head_command(self):
        """head command should be allowed."""
        result = validate_command("head -5 /path/file.txt")
        assert result.is_safe

    def test_grep_command(self):
        """grep command should be allowed."""
        result = validate_command("grep -r 'pattern' /path")
        assert result.is_safe

    def test_cat_command(self):
        """cat command should be allowed."""
        result = validate_command("cat /path/file.txt")
        assert result.is_safe


class TestBlockedCommands:
    """Test that blocked commands are rejected."""

    def test_rm_blocked(self):
        """rm command should be blocked."""
        result = validate_command("rm file.txt")
        assert not result.is_safe

    def test_sudo_blocked(self):
        """sudo command should be blocked."""
        result = validate_command("sudo ls")
        assert not result.is_safe

    def test_curl_blocked(self):
        """curl command should be blocked."""
        result = validate_command("curl https://example.com")
        assert not result.is_safe
