"""Tests for utility functions."""

import pytest
from pathlib import Path
from dbb.utils import (
    compute_sha256,
    ensure_dir_exists,
    write_file,
    read_file,
    delete_file,
    truncate_string,
    sanitize_filename,
)


def test_compute_sha256():
    """Test SHA-256 computation."""
    content = "test content"
    hash1 = compute_sha256(content)
    hash2 = compute_sha256(content)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex string length


def test_compute_sha256_different_content():
    """Test that different content produces different hashes."""
    hash1 = compute_sha256("content1")
    hash2 = compute_sha256("content2")

    assert hash1 != hash2


def test_ensure_dir_exists(tmp_path):
    """Test directory creation."""
    dir_path = tmp_path / "test" / "nested" / "dir"
    result = ensure_dir_exists(dir_path)

    assert result.exists()
    assert result.is_dir()


def test_write_and_read_file(tmp_path):
    """Test writing and reading files."""
    file_path = tmp_path / "test.txt"
    content = "test content"

    write_file(file_path, content)
    assert file_path.exists()

    read_content = read_file(file_path)
    assert read_content == content


def test_delete_file(tmp_path):
    """Test file deletion."""
    file_path = tmp_path / "test.txt"
    write_file(file_path, "test")

    result = delete_file(file_path)
    assert result is True
    assert not file_path.exists()


def test_delete_nonexistent_file(tmp_path):
    """Test deleting nonexistent file."""
    file_path = tmp_path / "nonexistent.txt"
    result = delete_file(file_path)
    assert result is False


def test_truncate_string():
    """Test string truncation."""
    long_string = "a" * 200
    truncated = truncate_string(long_string, 100)

    assert len(truncated) <= 100
    assert truncated.endswith("...")


def test_truncate_short_string():
    """Test truncating short string (should not truncate)."""
    short_string = "short"
    truncated = truncate_string(short_string, 100)

    assert truncated == short_string


def test_sanitize_filename():
    """Test filename sanitization."""
    filename = "my/file:name*.txt"
    sanitized = sanitize_filename(filename)

    assert "/" not in sanitized
    assert ":" not in sanitized
    assert "*" not in sanitized


def test_sanitize_filename_length():
    """Test filename length limit."""
    long_filename = "a" * 300 + ".txt"
    sanitized = sanitize_filename(long_filename)

    assert len(sanitized) <= 255
