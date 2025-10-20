"""Utility functions for hashing, logging, and file operations."""

import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def compute_sha256(content: str) -> str:
    """
    Compute SHA-256 hash of content.

    Args:
        content: String content to hash

    Returns:
        Hex string of SHA-256 hash
    """
    return hashlib.sha256(content.encode()).hexdigest()


def compute_file_sha256(file_path: Path) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex string of SHA-256 hash
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def ensure_dir_exists(path: Path) -> Path:
    """
    Ensure directory exists, create if not.

    Args:
        path: Directory path

    Returns:
        Path object (created or existing)
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Directory ensured at {path}")
    return path


def write_file(path: Path, content: str) -> Path:
    """
    Write content to file.

    Args:
        path: File path
        content: Content to write

    Returns:
        Path to written file
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.debug(f"File written to {path}")
    return path


def read_file(path: Path) -> str:
    """
    Read content from file.

    Args:
        path: File path

    Returns:
        File content as string
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return content


def delete_file(path: Path) -> bool:
    """
    Delete file safely.

    Args:
        path: File path

    Returns:
        True if deleted, False if file doesn't exist
    """
    path = Path(path)
    if path.exists():
        path.unlink()
        logger.debug(f"File deleted: {path}")
        return True
    logger.warning(f"File not found for deletion: {path}")
    return False


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as ISO string.

    Args:
        dt: Datetime object (uses now if None)

    Returns:
        ISO formatted datetime string
    """
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat() + "Z"


def parse_timestamp(ts: str) -> datetime:
    """
    Parse ISO timestamp string.

    Args:
        ts: ISO formatted datetime string

    Returns:
        Datetime object
    """
    # Remove 'Z' if present
    if ts.endswith("Z"):
        ts = ts[:-1]
    return datetime.fromisoformat(ts)


def truncate_string(s: str, length: int = 100) -> str:
    """
    Truncate string to maximum length.

    Args:
        s: String to truncate
        length: Maximum length

    Returns:
        Truncated string with ellipsis if needed
    """
    if len(s) > length:
        return s[:length-3] + "..."
    return s


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be safe for file systems.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Replace problematic characters
    sanitized = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
    # Remove leading/trailing dots
    sanitized = sanitized.strip(".")
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    return sanitized
