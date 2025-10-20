"""Tests for database operations."""

import pytest
from dbb.db import DatabaseManager


def test_database_initialization(test_db):
    """Test database initialization."""
    assert test_db.connection is not None


def test_insert_episode(test_db, sample_episode):
    """Test inserting an episode."""
    result = test_db.insert_episode(sample_episode)
    assert result is True

    # Try inserting duplicate
    result = test_db.insert_episode(sample_episode)
    assert result is False


def test_update_transcript(test_db, sample_episode, sample_transcript):
    """Test updating episode transcript."""
    test_db.insert_episode(sample_episode)

    transcript_data = {
        "transcript_md": sample_transcript,
        "provider": "test_provider",
        "language": "en",
        "checksum": "abc123",
        "length": len(sample_transcript),
        "path": "/test/path.md",
        "on_disk": True,
    }

    test_db.update_transcript(sample_episode["video_id"], transcript_data)

    # Verify update
    result = test_db.connection.execute(
        "SELECT transcript_md FROM episodes WHERE video_id = ?",
        [sample_episode["video_id"]]
    ).fetchall()

    assert len(result) == 1
    assert result[0][0] == sample_transcript


def test_get_episodes_without_transcript(test_db, sample_episode):
    """Test getting episodes without transcripts."""
    test_db.insert_episode(sample_episode)

    episodes = test_db.get_episodes_without_transcript()
    assert len(episodes) == 1
    assert episodes[0]["video_id"] == sample_episode["video_id"]


def test_get_stats(test_db, sample_episode):
    """Test getting database statistics."""
    test_db.insert_episode(sample_episode)

    stats = test_db.get_stats()
    assert stats["total_episodes"] == 1
    assert stats["episodes_with_transcripts"] == 0
    assert stats["episodes_with_summaries"] == 0


def test_context_manager(test_config):
    """Test database context manager."""
    with DatabaseManager(test_config) as db:
        assert db is not None
        db.init_schema()

    # Connection should be closed after context
