"""Safe dynamic module loading for generated scripts."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from mega_ai.worker.exceptions import ScriptLoadError


def load_script(script_path: Path, module_name: str) -> ModuleType:
    """
    Safely load a Python script as a module.

    Args:
        script_path: Path to the .py file
        module_name: Name to assign to the module (e.g., 'runner', 'backup')

    Returns:
        The loaded module

    Raises:
        ScriptLoadError: If script doesn't exist or fails to load
    """
    if not script_path.exists():
        raise ScriptLoadError(f"Script not found: {script_path}")

    if script_path.suffix != ".py":
        raise ScriptLoadError(f"Not a Python file: {script_path}")

    try:
        # Create unique module name to avoid collisions
        full_module_name = f"mega_ai.worker.loaded.{module_name}"

        # Load spec from file
        spec = importlib.util.spec_from_file_location(full_module_name, script_path)
        if spec is None or spec.loader is None:
            raise ScriptLoadError(f"Cannot create spec for: {script_path}")

        # Create and execute module
        module = importlib.util.module_from_spec(spec)
        sys.modules[full_module_name] = module
        spec.loader.exec_module(module)

        return module

    except SyntaxError as e:
        raise ScriptLoadError(f"Syntax error in {script_path}: {e}") from e
    except ImportError as e:
        raise ScriptLoadError(f"Import error in {script_path}: {e}") from e
    except Exception as e:
        raise ScriptLoadError(f"Failed to load {script_path}: {e}") from e


def validate_runner_script(module: ModuleType) -> None:
    """
    Validate that runner module has required interface.

    Raises:
        ScriptLoadError: If validation fails
    """
    if not hasattr(module, "run"):
        raise ScriptLoadError("runner.py must have a 'run(dry_run=False)' function")

    if not callable(module.run):
        raise ScriptLoadError("runner.py 'run' must be callable")


def validate_backup_script(module: ModuleType) -> None:
    """
    Validate that backup module has required interface.

    Raises:
        ScriptLoadError: If validation fails
    """
    if not hasattr(module, "backup"):
        raise ScriptLoadError("backup.py must have a 'backup()' function")

    if not hasattr(module, "restore"):
        raise ScriptLoadError("backup.py must have a 'restore()' function")

    if not callable(module.backup) or not callable(module.restore):
        raise ScriptLoadError("backup.py 'backup' and 'restore' must be callable")
