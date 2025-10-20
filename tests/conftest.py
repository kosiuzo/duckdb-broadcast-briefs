"""Pytest fixtures for DuckDB Broadcast Briefs."""

import tempfile
from pathlib import Path
import pytest
from dbb.config import Config, ChannelConfig, FetchConfig, TranscriptsConfig
from dbb.config import SummarizeConfig, EmailConfig, SmtpConfig, LoggingConfig
from dbb.db import DatabaseManager


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        yield db_path


@pytest.fixture
def test_config(temp_db_path):
    """Create a test configuration."""
    return Config(
        db_path=str(temp_db_path),
        data_dir="./test_data",
        transcript_dir="./test_data/transcripts",
        summary_dir="./test_data/summaries",
        channels=[
            ChannelConfig(
                name="Test Channel",
                channel_id="UCTest123"
            )
        ],
        fetch=FetchConfig(
            use_youtube_api=True,
            api_key_env="YOUTUBE_API_KEY",
            max_per_channel=None
        ),
        transcripts_providers=TranscriptsConfig(),
        summarize=SummarizeConfig(),
        email=EmailConfig(),
        smtp=SmtpConfig(),
        logging=LoggingConfig()
    )


@pytest.fixture
def test_db(test_config):
    """Create a test database with schema."""
    db = DatabaseManager(test_config)
    db.connect()
    db.init_schema()
    db.ensure_directories()
    yield db
    db.close()


@pytest.fixture
def sample_episode():
    """Create a sample episode for testing."""
    return {
        "video_id": "test123",
        "channel_id": "UCTest123",
        "channel_title": "Test Channel",
        "title": "Test Episode",
        "url": "https://www.youtube.com/watch?v=test123",
        "published_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_transcript():
    """Create a sample transcript."""
    return """
    This is a test transcript.
    It contains multiple lines.
    And various content to simulate a real podcast transcript.
    """
