"""File picker utilities for V2 guided wizards.

Provides directory scanning, file listing with size metadata, and drag-and-drop
path cleaning for Windows quoted paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.cli_v2.navigation import NavigationEngine
from src.utils.file_handler import FileHandler


class FilePicker:
    """Hybrid file picker: directory enumeration + custom path entry."""

    # Default exclusion patterns for batch operations
    DEFAULT_EXCLUDE_EXTENSIONS = {
        ".key", ".iv", ".log", ".tmp", ".enc"
    }

    # OS metadata files to always exclude
    OS_METADATA_FILES = {
        ".DS_Store", "Thumbs.db", "desktop.ini"
    }

    @staticmethod
    def _is_cancel(raw: str) -> bool:
        """True when the complete input token is the universal cancellation token.

        The universal navigation token (``c`` / ``cancel``, as defined by
        :class:`~src.cli_v2.navigation.NavigationEngine`) takes precedence over
        any local FilePicker keyword. Exact-token match only — a filesystem path
        is never interpreted as the cancellation command.
        """
        return raw.strip().lower() in NavigationEngine.CANCEL_TOKENS

    @staticmethod
    def clean_path(user_input: str) -> Path:
        """Strip enclosing single/double quotes and whitespace from drag-and-drop paths.

        Args:
            user_input: Raw user input possibly containing quoted path.

        Returns:
            Path object with quotes and whitespace stripped.
        """
        cleaned = user_input.strip()

        # Strip matching pairs of quotes
        if len(cleaned) >= 2:
            if (cleaned[0] == '"' and cleaned[-1] == '"') or \
               (cleaned[0] == "'" and cleaned[-1] == "'"):
                cleaned = cleaned[1:-1]

        return Path(cleaned.strip())

    @staticmethod
    def list_files(
        directory: Path,
        pattern: str = "*",
        exclude_extensions: Optional[set[str]] = None,
        include_hidden: bool = False
    ) -> list[tuple[Path, int]]:
        """Return list of (Path, size_bytes) sorted alphabetically by filename.

        Args:
            directory: Directory to scan.
            pattern: Glob pattern for file matching.
            exclude_extensions: Set of file extensions to exclude (default: DEFAULT_EXCLUDE_EXTENSIONS).
            include_hidden: Whether to include hidden files (starting with '.'). Default False.

        Returns:
            List of (Path, size_bytes) tuples sorted by filename (case-insensitive).
        """
        if exclude_extensions is None:
            exclude_extensions = FilePicker.DEFAULT_EXCLUDE_EXTENSIONS.copy()

        if not directory.exists() or not directory.is_dir():
            return []

        files: list[tuple[Path, int]] = []

        for entry in directory.iterdir():
            if not entry.is_file():
                continue

            # Skip hidden files unless explicitly included
            if not include_hidden and entry.name.startswith("."):
                continue

            # Skip OS metadata files
            if entry.name in FilePicker.OS_METADATA_FILES:
                continue

            # Skip by extension
            if entry.suffix.lower() in exclude_extensions:
                continue

            try:
                size = entry.stat().st_size
                files.append((entry, size))
            except OSError:
                # Skip files that can't be stat'd
                continue

        # Sort alphabetically by filename (case-insensitive)
        files.sort(key=lambda x: x[0].name.lower())
        return files

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format byte size as human-readable string.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Formatted string (e.g., "1.5 KB", "2.0 MB").
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    @staticmethod
    def display_file_list(files: list[tuple[Path, int]], title: str = "Available files") -> None:
        """Display a numbered file list with sizes.

        Args:
            files: List of (Path, size_bytes) tuples.
            title: Title to display above the list.
        """
        if not files:
            print(f"\n{title}: (none)")
            return

        print(f"\n{title}:")
        for i, (path, size) in enumerate(files, 1):
            size_str = FilePicker.format_size(size)
            print(f"  {i}. {path.name} ({size_str})")

    @staticmethod
    def prompt_file_selection(
        files: list[tuple[Path, int]],
        prompt: str = "Select file",
        allow_custom: bool = True
    ) -> Optional[Path]:
        """Prompt user to select a file from the list or enter a custom path.

        Args:
            files: List of (Path, size_bytes) tuples.
            prompt: Prompt text.
            allow_custom: Whether to allow custom path entry.

        Returns:
            Selected Path, or None if cancelled.
        """
        if not files:
            print("  No files available.")
            if not allow_custom:
                return None

        FilePicker.display_file_list(files)

        custom_option_index = len(files) + 1 if allow_custom else None

        while True:
            try:
                if allow_custom:
                    raw = input(f"{prompt} [1-{len(files)} or {custom_option_index} for custom]: ").strip()
                else:
                    raw = input(f"{prompt} [1-{len(files)}]: ").strip()
            except EOFError:
                return None

            if not raw:
                continue

            # Try numeric selection first
            try:
                choice = int(raw)
                if 1 <= choice <= len(files):
                    return files[choice - 1][0]
                elif allow_custom and choice == custom_option_index:
                    # Custom path option selected
                    custom = input("  Enter custom path: ").strip()
                    if FilePicker._is_cancel(custom):
                        return None
                    if custom:
                        return FilePicker.clean_path(custom)
                    continue
                else:
                    max_val = custom_option_index if allow_custom else len(files)
                    print(f"  Enter a number between 1 and {max_val}")
                    continue
            except ValueError:
                # Not a number. Order matters:
                #   1. The universal cancellation token takes precedence and is
                #      never routed to custom-path mode.
                #   2. The "custom" keyword enters custom-path mode (if allowed).
                #   3. Anything else is invalid numeric input.
                if FilePicker._is_cancel(raw):
                    return None
                if allow_custom and raw.lower() == "custom":
                    custom = input("  Enter custom path: ").strip()
                    if FilePicker._is_cancel(custom):
                        return None
                    if custom:
                        return FilePicker.clean_path(custom)
                    continue
                print(f"  Enter a number between 1 and {custom_option_index if allow_custom else len(files)}")
                continue

    @staticmethod
    def resolve_input_path(
        directory: Path,
        default_dir_name: str = "data/input",
        pattern: str = "*",
        exclude_extensions: Optional[set[str]] = None
    ) -> Path:
        """Resolve input file path via picker or custom entry.

        Args:
            directory: Default directory to scan.
            default_dir_name: Display name for default directory.
            pattern: Glob pattern for file matching.
            exclude_extensions: Extensions to exclude.

        Returns:
            Selected or entered Path.
        """
        # Ensure directory exists
        FileHandler.ensure_directory(directory)

        files = FilePicker.list_files(directory, pattern, exclude_extensions)

        print(f"\nScanning {default_dir_name}/ ...")
        FilePicker.display_file_list(files, f"Files in {default_dir_name}")

        while True:
            try:
                raw = input("\nEnter file number or custom path: ").strip()
            except EOFError:
                raise KeyboardInterrupt("User cancelled")

            if not raw:
                continue

            # Universal cancellation token takes precedence and propagates via
            # the same KeyboardInterrupt signal used for EOF cancellation.
            if FilePicker._is_cancel(raw):
                raise KeyboardInterrupt("User cancelled")

            # Try numeric selection
            try:
                choice = int(raw)
                if 1 <= choice <= len(files):
                    return files[choice - 1][0]
                # Number out of range - treat as custom path
                print(f"  Enter a number between 1 and {len(files)} or a custom path")
                continue
            except ValueError:
                pass

            # Treat as custom path
            return FilePicker.clean_path(raw)

    @staticmethod
    def resolve_output_path(
        directory: Path,
        suggested_name: str,
        default_dir_name: str = "data/output"
    ) -> Path:
        """Resolve output file path with overwrite check.

        Args:
            directory: Output directory.
            suggested_name: Suggested filename.
            default_dir_name: Display name for default directory.

        Returns:
            Resolved output Path.
        """
        FileHandler.ensure_directory(directory)
        output_path = directory / suggested_name

        if output_path.exists():
            print(f"\n[!] Conflict: '{output_path}' already exists.")
            while True:
                try:
                    raw = input("  [1] Overwrite, [2] Enter new name, [3] Cancel: ").strip()
                except EOFError:
                    raise KeyboardInterrupt("User cancelled")

                if raw == "1":
                    return output_path
                elif raw == "2":
                    new_name = input("  Enter new filename: ").strip()
                    if new_name:
                        return directory / new_name
                elif raw == "3":
                    raise KeyboardInterrupt("User cancelled")
                else:
                    print("  Enter 1, 2, or 3")
        else:
            return output_path