"""
Resource Manager Module

Provides a facade for managing application resources (files) located in the resources directory.
Supports scoped resources and lazy file operations.

Example usage:
    # Get a resource file reference
    resource = Resources.get("config.json")

    # Get a scoped resource
    resource = Resources.get("settings.yaml", scope="admin")

    # Get absolute path without opening the file
    path = resource.path

    # Read content (opens file)
    content = resource.read()
    text = resource.read_text()
    data = resource.read_json()

    # Write content (opens file)
    resource.write(b"binary data")
    resource.write_text("text content")
    resource.write_json({"key": "value"})

    # Check existence
    exists = resource.exists()

    # Use as context manager for automatic closing
    with Resources.get("data.txt") as resource:
        content = resource.read_text()
"""

import json
from pathlib import Path
from typing import IO, Any


class FileOpenError(Exception):
    pass


class ResourceFile:
    """
    Represents a resource file with lazy operations.

    The file is not opened until an operation that requires it is performed.
    Provides methods for reading, writing, and getting file information.
    """

    def __init__(self, path: Path, auto_seek_reset: bool = False):
        """
        Initialize a ResourceFile instance.

        Args:
            path: Absolute path to the resource file.
        """
        self._path = path
        self._file: IO[Any] | None = None

        self.auto_seek_reset = auto_seek_reset

    @property
    def path(self) -> Path:
        """Get the absolute path to the resource file."""
        return self._path

    @property
    def name(self) -> str:
        """Get the file name."""
        return self._path.name

    @property
    def stem(self) -> str:
        """Get the file name without extension."""
        return self._path.stem

    @property
    def suffix(self) -> str:
        """Get the file extension."""
        return self._path.suffix

    def exists(self) -> bool:
        """Check if the resource file exists."""
        return self._path.exists()

    def is_file(self) -> bool:
        """Check if the resource path is a file."""
        return self._path.is_file()

    def is_dir(self) -> bool:
        """Check if the resource path is a directory."""
        return self._path.is_dir()

    def parent(self) -> Path:
        """Get the parent directory path."""
        return self._path.parent

    def _ensure_dir(self):
        """Ensure the parent directory exists."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def fopen(self, mode: str = 'r', **kwargs) -> 'ResourceFile':
        """
        Open the file and return self for method chaining.

        Args:
            mode: File open mode ('r', 'w', 'a', 'rb', 'wb', etc.)
            **kwargs: Additional arguments passed to Path.open()

        Returns:
            Self for method chaining.
        """
        if self._file is not None:
            self._file.close()

        self._ensure_dir()
        self._file = self._path.open(mode, **kwargs)
        if not self._file:
            raise FileOpenError(f"Can not open a file: {self._path}")

        return self

    def fclose(self):
        """Close the file if it's open."""
        if self._file is not None:
            self._file.close()
            self._file = None

    def seek(self, position: int = 0):
        if self._file is not None:
            self._file.seek(position)

    def read_text(self, encoding: str = 'utf-8', seek: int | None = None) -> str:
        """
        Read text content from the file.

        Args:
            encoding: Text encoding (default: utf-8).
            seek: Do 'seek' operation before reading.

        Returns:
            Text content of the file.

        Raises:
            Any exception raised by file operations (e.g., FileNotFoundError,
            PermissionError, IOError, UnicodeDecodeError). The file is automatically closed on error.
        """
        try:
            if self._file is None:
                self.fopen('r', encoding=encoding)

            if seek is not None:
                self.seek(seek)
            elif self.auto_seek_reset:
                self.seek(0)

            return self._file.read()  # type: ignore[union-attr]
        except Exception:
            self.fclose()
            raise

    def read_json(self, encoding: str = 'utf-8') -> Any:
        """
        Read and parse JSON content from the file.

        Args:
            encoding: Text encoding (default: utf-8).

        Returns:
            Parsed JSON data.
        """
        return json.loads(self.read_text(encoding, 0))

    def write_text(self, text: str, encoding: str = 'utf-8') -> int:
        """
        Write text content to the file.

        Args:
            text: Text content to write.
            encoding: Text encoding (default: utf-8).

        Returns:
            Number of characters written.

        Raises:
            Any exception raised by file operations (e.g., PermissionError,
            IOError, OSError, UnicodeEncodeError). The file is automatically closed on error.
        """
        try:
            if self._file is None:
                self.fopen('w', encoding=encoding)
            return self._file.write(text)  # type: ignore[union-attr]
        except Exception:
            self.fclose()
            raise

    def write_json(self, data: Any, encoding: str = 'utf-8', indent: int = 2, **kwargs) -> int:
        """
        Serialize and write JSON data to the file.

        Args:
            data: Data to serialize as JSON.
            encoding: Text encoding (default: utf-8).
            indent: JSON indentation (default: 2).
            **kwargs: Additional arguments passed to json.dump().

        Returns:
            Number of characters written.
        """
        text = json.dumps(data, indent=indent, **kwargs)
        return self.write_text(text, encoding)

    def readlines(self, encoding: str = 'utf-8', seek: int | None = None) -> list[str]:
        """
        Read all lines from the file.

        Args:
            encoding: Text encoding (default: utf-8).
            seek: Do 'seek' operation before reading.

        Returns:
            List of lines.

        Raises:
            Any exception raised by file operations (e.g., FileNotFoundError,
            PermissionError, IOError, UnicodeDecodeError). The file is automatically closed on error.
        """
        try:
            if self._file is None:
                self.fopen('r', encoding=encoding)

            if seek is not None:
                self.seek(seek)
            elif self.auto_seek_reset:
                self.seek(0)

            return self._file.readlines()  # type: ignore[union-attr]
        except Exception:
            self.fclose()
            raise

    def writelines(self, lines: list[str], encoding: str = 'utf-8'):
        """
        Write lines to the file.

        Args:
            lines: List of lines to write.
            encoding: Text encoding (default: utf-8).

        Raises:
            Any exception raised by file operations (e.g., PermissionError,
            IOError, OSError, UnicodeEncodeError). The file is automatically closed on error.
        """
        try:
            if self._file is None:
                self.fopen('w', encoding=encoding)
            self._file.writelines(lines)  # type: ignore[union-attr]
        except Exception:
            self.fclose()
            raise

    def __enter__(self) -> 'ResourceFile':
        """
        Context manager entry - opens the file in read mode by default.

        For custom modes, use open_for() method or call open() directly.

        Returns:
            Self for use within the with block.
        """
        if self._file is None:
            self.fopen('r')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - closes the file.

        If an exception occurred within the with block, the file is closed
        before the exception is propagated further.

        Args:
            exc_type: Exception type if an exception occurred, None otherwise.
            exc_val: Exception value if an exception occurred, None otherwise.
            exc_tb: Exception traceback if an exception occurred, None otherwise.

        Returns:
            False to propagate any exception, None/True to suppress it.
        """
        self.fclose()

    def open_for(self, mode: str = 'r', **kwargs) -> 'ResourceFile':
        """
        Open the file for a specific operation and return self for use in with statements.

        This method is useful when you need to use the context manager with
        a specific mode other than 'r'.

        Args:
            mode: File open mode ('r', 'w', 'a', 'rb', 'wb', etc.)
            **kwargs: Additional arguments passed to Path.open()

        Returns:
            Self for use in with statements.

        Example:
            >>> with resource.open_for('w') as f:
            ...     f.write_text("data")
            >>>
            >>> with resource.open_for('rb') as f:
            ...     data = f.read()
        """
        self.fopen(mode, **kwargs)
        return self

    def __repr__(self) -> str:
        return f"ResourceFile(path={self._path!r})"

    def __str__(self) -> str:
        return str(self._path)


class Resources:
    """
    Facade for accessing application resources.

    Provides a simple API to get resource files from the resources directory.
    Supports optional scoping for organized resource management.

    Example usage:
        # Get a resource from the root resources directory
        config = Resources.get("config.json")

        # Get a scoped resource
        admin_config = Resources.get("settings.yaml", scope="admin")

        # Read content
        if config.exists():
            data = config.read_json()
    """

    _base_path: Path | None = None

    @classmethod
    def set_base_path(cls, path: str | Path):
        """
        Set the base path for resources directory.

        Args:
            path: Base path where the resources directory is located.
        """
        cls._base_path = Path(path).resolve()

    @classmethod
    def get_base_path(cls) -> Path:
        """
        Get the base path for resources directory.

        Returns:
            Base path, defaults to the project root if not explicitly set.
        """
        if cls._base_path is None:
            # Auto-detect: go up from apps/module_shared to project root
            current = Path(__file__).resolve()
            # Navigate up to find the project root (where apps/ is located)
            while current.parent.name != '' and not (current.parent / 'apps').exists():
                current = current.parent
            cls._base_path = current.parent if current.parent.name != '' else current
        return cls._base_path

    @classmethod
    def get_resources_dir(cls) -> Path:
        """
        Get the resources directory path.

        Returns:
            Path to the resources directory.
        """
        return cls.get_base_path() / 'resources'

    @classmethod
    def get(cls, source_name: str, scope: str | None = None) -> ResourceFile:
        """
        Get a resource file reference.

        This method does not open or verify the file existence.
        It returns a ResourceFile object that can be used for lazy operations.

        Args:
            source_name: Name of the resource file (e.g., "config.json").
            scope: Optional scope/subdirectory (e.g., "admin", "user").
                   If provided, the file will be looked up in resources/<scope>/.

        Returns:
            ResourceFile object for the specified resource.

        Example:
            >>> resource = Resources.get("data.txt")
            >>> resource = Resources.get("settings.yaml", scope="admin")
            >>> print(resource.path)  # Absolute path without opening file
            >>> content = resource.read_text()  # Opens, reads, and closes automatically
        """
        resources_dir = cls.get_resources_dir()

        if scope:
            file_path = resources_dir / scope / source_name
        else:
            file_path = resources_dir / source_name

        return ResourceFile(file_path.resolve())

    @classmethod
    def get_scoped(cls, scope: str) -> 'ScopedResources':
        """
        Get a scoped resources helper.

        Args:
            scope: The scope name to use for all subsequent get() calls.

        Returns:
            ScopedResources instance for convenient access to scoped resources.

        Example:
            >>> admin = Resources.get_scoped("admin")
            >>> config = admin.get("settings.yaml")  # Equivalent to Resources.get("settings.yaml", scope="admin")
        """
        return ScopedResources(scope)

    @classmethod
    def list_resources(cls, scope: str | None = None, pattern: str = '*') -> list[Path]:
        """
        List resources matching a pattern.

        Args:
            scope: Optional scope to search in.
            pattern: Glob pattern for filtering (default: '*').

        Returns:
            List of paths to matching resources.
        """
        resources_dir = cls.get_resources_dir()
        if scope:
            resources_dir = resources_dir / scope

        if not resources_dir.exists():
            return []

        return list(resources_dir.glob(pattern))


class ScopedResources:
    """
    Helper class for working with a specific resource scope.

    Provides a convenient way to access multiple resources within the same scope
    without repeatedly specifying the scope parameter.
    """

    def __init__(self, scope: str):
        """
        Initialize a scoped resources helper.

        Args:
            scope: The scope name for all resource operations.
        """
        self.scope = scope

    def get(self, source_name: str) -> ResourceFile:
        """
        Get a resource file within this scope.

        Args:
            source_name: Name of the resource file.

        Returns:
            ResourceFile object for the specified resource.
        """
        return Resources.get(source_name, scope=self.scope)

    def list_resources(self, pattern: str = '*') -> list[Path]:
        """
        List resources in this scope matching a pattern.

        Args:
            pattern: Glob pattern for filtering (default: '*').

        Returns:
            List of paths to matching resources.
        """
        return Resources.list_resources(scope=self.scope, pattern=pattern)

    def __repr__(self) -> str:
        return f"ScopedResources(scope={self.scope!r})"


# Convenience function for quick access
def get_resource(source_name: str, scope: str | None = None) -> ResourceFile:
    """
    Quick access to a resource file.

    This is a convenience wrapper around Resources.get().

    Args:
        source_name: Name of the resource file.
        scope: Optional scope/subdirectory.

    Returns:
        ResourceFile object for the specified resource.
    """
    return Resources.get(source_name, scope=scope)


__all__ = [
    'Resources',
    'ResourceFile',
    'ScopedResources',
    'get_resource',
]
