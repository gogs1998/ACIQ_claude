"""
Workspace management for AccountantIQ multi-agent system.
Handles workspace creation, configuration, and state management.
"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from accountantiq.core.models import WorkspaceConfig
from accountantiq.core.database import Database


class Workspace:
    """Manages workspace directory structure and configuration."""

    def __init__(self, workspace_name: str, base_path: Optional[str] = None):
        """
        Initialize workspace.

        Args:
            workspace_name: Name of the workspace
            base_path: Base path for workspaces (defaults to ./data/workspaces)
        """
        if base_path is None:
            base_path = Path(__file__).parent.parent / "data" / "workspaces"
        else:
            base_path = Path(base_path)

        self.workspace_name = workspace_name
        self.workspace_path = base_path / workspace_name
        self.config_file = self.workspace_path / "config.json"
        self.db_file = self.workspace_path / "accountant.db"

    def exists(self) -> bool:
        """Check if workspace exists."""
        return self.workspace_path.exists() and self.config_file.exists()

    def create(self, overwrite: bool = False) -> "Workspace":
        """
        Create workspace directory structure and initialize database.

        Args:
            overwrite: If True, overwrite existing workspace

        Returns:
            Self for chaining
        """
        if self.exists() and not overwrite:
            raise ValueError(f"Workspace '{self.workspace_name}' already exists")

        # Create directory structure
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        (self.workspace_path / "exports").mkdir(exist_ok=True)
        (self.workspace_path / "imports").mkdir(exist_ok=True)
        (self.workspace_path / "logs").mkdir(exist_ok=True)

        # Initialize configuration
        config = WorkspaceConfig(
            name=self.workspace_name,
            created_at=datetime.now()
        )
        self._save_config(config)

        # Initialize database
        db = Database(str(self.db_file))
        db.close()

        return self

    def load(self) -> "Workspace":
        """
        Load existing workspace.

        Returns:
            Self for chaining

        Raises:
            ValueError: If workspace doesn't exist
        """
        if not self.exists():
            raise ValueError(f"Workspace '{self.workspace_name}' does not exist")
        return self

    def get_config(self) -> WorkspaceConfig:
        """Get workspace configuration."""
        if not self.config_file.exists():
            raise ValueError(f"Workspace '{self.workspace_name}' not initialized")

        with open(self.config_file, 'r') as f:
            config_data = json.load(f)

        return WorkspaceConfig(**config_data)

    def update_config(self, **kwargs):
        """Update workspace configuration."""
        config = self.get_config()

        # Update fields
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.last_modified = datetime.now()
        self._save_config(config)

    def _save_config(self, config: WorkspaceConfig):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(config.to_dict(), f, indent=2, default=str)

    def get_database(self) -> Database:
        """Get database connection for this workspace."""
        if not self.exists():
            raise ValueError(f"Workspace '{self.workspace_name}' does not exist")
        return Database(str(self.db_file))

    def _validate_filename(self, filename: str) -> str:
        """
        Validate filename to prevent path traversal attacks.

        Args:
            filename: Filename to validate

        Returns:
            Safe filename (just the name component)

        Raises:
            ValueError: If filename is invalid or contains path components
        """
        if not filename:
            raise ValueError("Filename cannot be empty")

        # SECURITY FIX: Extract only the filename component (no path traversal)
        safe_name = Path(filename).name

        # Ensure the filename didn't contain any path components
        if safe_name != filename or not safe_name:
            raise ValueError(f"Invalid filename (contains path components): {filename}")

        # Prevent hidden files
        if safe_name.startswith('.'):
            raise ValueError(f"Filename cannot start with dot: {filename}")

        return safe_name

    def get_export_path(self, filename: str) -> Path:
        """Get path for export file with path traversal protection."""
        safe_name = self._validate_filename(filename)
        return self.workspace_path / "exports" / safe_name

    def get_import_path(self, filename: str) -> Path:
        """Get path for import file with path traversal protection."""
        safe_name = self._validate_filename(filename)
        return self.workspace_path / "imports" / safe_name

    def get_log_path(self, filename: str) -> Path:
        """Get path for log file with path traversal protection."""
        safe_name = self._validate_filename(filename)
        return self.workspace_path / "logs" / safe_name

    def delete(self, confirm: bool = False):
        """
        Delete workspace.

        Args:
            confirm: Must be True to actually delete

        Raises:
            ValueError: If confirm is not True
        """
        if not confirm:
            raise ValueError("Must set confirm=True to delete workspace")

        if self.workspace_path.exists():
            import shutil
            shutil.rmtree(self.workspace_path)

    def __str__(self) -> str:
        """String representation."""
        return f"Workspace(name='{self.workspace_name}', path='{self.workspace_path}')"

    def __repr__(self) -> str:
        """Detailed representation."""
        return self.__str__()


class WorkspaceManager:
    """Manages multiple workspaces."""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize workspace manager.

        Args:
            base_path: Base path for workspaces
        """
        if base_path is None:
            base_path = Path(__file__).parent.parent / "data" / "workspaces"
        else:
            base_path = Path(base_path)

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def list_workspaces(self) -> list[str]:
        """List all available workspaces."""
        workspaces = []
        for path in self.base_path.iterdir():
            if path.is_dir() and (path / "config.json").exists():
                workspaces.append(path.name)
        return sorted(workspaces)

    def get_workspace(self, name: str) -> Workspace:
        """Get workspace by name."""
        return Workspace(name, str(self.base_path))

    def create_workspace(self, name: str, overwrite: bool = False) -> Workspace:
        """Create a new workspace."""
        workspace = Workspace(name, str(self.base_path))
        workspace.create(overwrite=overwrite)
        return workspace

    def delete_workspace(self, name: str, confirm: bool = False):
        """Delete a workspace."""
        workspace = Workspace(name, str(self.base_path))
        workspace.delete(confirm=confirm)

    def workspace_exists(self, name: str) -> bool:
        """Check if workspace exists."""
        workspace = Workspace(name, str(self.base_path))
        return workspace.exists()
