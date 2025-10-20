"""DuckDB database management and schema operations."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

import duckdb

from dbb.config import Config
from dbb.utils import ensure_dir_exists, format_timestamp

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages DuckDB database operations."""

    def __init__(self, config: Config):
        """
        Initialize database manager.

        Args:
            config: Application configuration
        """
        self.config = config
        self.db_path = Path(config.db_path)
        self.connection = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        """
        Connect to DuckDB database.

        Returns:
            DuckDB connection object
        """
        self.connection = duckdb.connect(str(self.db_path))
        logger.info(f"Connected to database at {self.db_path}")
        return self.connection

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.debug("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def init_schema(self) -> None:
        """Initialize database schema (create tables and indexes)."""
        if not self.connection:
            self.connect()

        logger.info("Initializing database schema...")

        # Create episodes table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                -- Identity & catalog
                video_id            TEXT PRIMARY KEY,
                channel_id          TEXT,
                channel_title       TEXT,
                title               TEXT,
                url                 TEXT,
                published_at        TIMESTAMP,
                fetched_at          TIMESTAMP,

                -- Transcript (API-only)
                transcript_md       TEXT,
                transcript_provider TEXT,
                transcript_language TEXT,
                transcript_checksum TEXT,
                transcript_length   INTEGER,
                transcript_path     TEXT,
                transcript_on_disk  BOOLEAN,

                -- Summary (local via Ollama)
                summary_md          TEXT,
                summary_model       TEXT,
                summary_created_at  TIMESTAMP,

                -- Bookkeeping
                updated_at          TIMESTAMP
            )
        """)

        # Create indexes
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_channel_date
                ON episodes (channel_title, published_at DESC)
        """)

        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodes_summary_created
                ON episodes (summary_created_at DESC)
        """)

        logger.info("Database schema initialized successfully")

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        ensure_dir_exists(Path(self.config.data_dir))
        ensure_dir_exists(Path(self.config.transcript_dir))
        ensure_dir_exists(Path(self.config.summary_dir))
        logger.info("Data directories ensured")

    def insert_episode(self, episode_data: Dict[str, Any]) -> bool:
        """
        Insert episode (idempotent).

        Args:
            episode_data: Episode data dictionary

        Returns:
            True if inserted, False if already exists
        """
        if not self.connection:
            self.connect()

        # Check if episode already exists
        result = self.connection.execute(
            "SELECT COUNT(*) as cnt FROM episodes WHERE video_id = ?",
            [episode_data["video_id"]]
        ).fetchall()

        if result[0][0] > 0:
            logger.debug(f"Episode {episode_data['video_id']} already exists, skipping")
            return False

        # Insert episode
        self.connection.execute("""
            INSERT INTO episodes (
                video_id, channel_id, channel_title, title, url,
                published_at, fetched_at, updated_at,
                transcript_on_disk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            episode_data.get("video_id"),
            episode_data.get("channel_id"),
            episode_data.get("channel_title"),
            episode_data.get("title"),
            episode_data.get("url"),
            episode_data.get("published_at"),
            episode_data.get("fetched_at", format_timestamp()),
            format_timestamp(),
            False
        ])

        logger.debug(f"Episode inserted: {episode_data['video_id']}")
        return True

    def update_transcript(self, video_id: str, transcript_data: Dict[str, Any]) -> None:
        """
        Update episode with transcript data.

        Args:
            video_id: Episode video ID
            transcript_data: Transcript information
        """
        if not self.connection:
            self.connect()

        self.connection.execute("""
            UPDATE episodes SET
                transcript_md = ?,
                transcript_provider = ?,
                transcript_language = ?,
                transcript_checksum = ?,
                transcript_length = ?,
                transcript_path = ?,
                transcript_on_disk = ?,
                updated_at = ?
            WHERE video_id = ?
        """, [
            transcript_data.get("transcript_md"),
            transcript_data.get("provider"),
            transcript_data.get("language", "en"),
            transcript_data.get("checksum"),
            transcript_data.get("length"),
            transcript_data.get("path"),
            transcript_data.get("on_disk", True),
            format_timestamp(),
            video_id
        ])

        logger.debug(f"Transcript updated for {video_id}")

    def update_summary(self, video_id: str, summary_data: Dict[str, Any]) -> None:
        """
        Update episode with summary data.

        Args:
            video_id: Episode video ID
            summary_data: Summary information
        """
        if not self.connection:
            self.connect()

        self.connection.execute("""
            UPDATE episodes SET
                summary_md = ?,
                summary_model = ?,
                summary_created_at = ?,
                updated_at = ?
            WHERE video_id = ?
        """, [
            summary_data.get("summary_md"),
            summary_data.get("model"),
            format_timestamp(),
            format_timestamp(),
            video_id
        ])

        logger.debug(f"Summary updated for {video_id}")

    def get_episodes_without_transcript(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get episodes without transcripts.

        Args:
            limit: Maximum number of episodes to return

        Returns:
            List of episode records
        """
        if not self.connection:
            self.connect()

        results = self.connection.execute("""
            SELECT video_id, url, title, channel_title
            FROM episodes
            WHERE transcript_md IS NULL
            ORDER BY COALESCE(published_at, fetched_at) DESC
            LIMIT ?
        """, [limit]).fetchall()

        columns = ["video_id", "url", "title", "channel_title"]
        return [dict(zip(columns, row)) for row in results]

    def get_episodes_without_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get episodes with transcripts but without summaries.

        Args:
            limit: Maximum number of episodes to return

        Returns:
            List of episode records
        """
        if not self.connection:
            self.connect()

        results = self.connection.execute("""
            SELECT video_id, title, channel_title, transcript_md
            FROM episodes
            WHERE transcript_md IS NOT NULL AND summary_md IS NULL
            ORDER BY COALESCE(published_at, fetched_at) DESC
            LIMIT ?
        """, [limit]).fetchall()

        columns = ["video_id", "title", "channel_title", "transcript_md"]
        return [dict(zip(columns, row)) for row in results]

    def get_recent_summaries(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get recently created summaries for digest.

        Args:
            days: Number of days to look back

        Returns:
            List of episode records grouped by channel
        """
        if not self.connection:
            self.connect()

        results = self.connection.execute("""
            SELECT
                video_id, channel_title, title, url, published_at,
                summary_md, transcript_path
            FROM episodes
            WHERE summary_created_at >= NOW() - INTERVAL ? DAY
            ORDER BY channel_title, COALESCE(published_at, fetched_at) DESC
        """, [days]).fetchall()

        columns = ["video_id", "channel_title", "title", "url", "published_at", "summary_md", "transcript_path"]
        return [dict(zip(columns, row)) for row in results]

    def get_episodes_with_transcript_on_disk(self) -> List[Dict[str, Any]]:
        """
        Get episodes with transcripts marked as on disk.

        Returns:
            List of episode records
        """
        if not self.connection:
            self.connect()

        results = self.connection.execute("""
            SELECT video_id, transcript_path, transcript_checksum
            FROM episodes
            WHERE transcript_on_disk = true AND transcript_path IS NOT NULL
        """).fetchall()

        columns = ["video_id", "transcript_path", "transcript_checksum"]
        return [dict(zip(columns, row)) for row in results]

    def set_transcript_on_disk(self, video_id: str, on_disk: bool) -> None:
        """
        Update transcript_on_disk flag.

        Args:
            video_id: Episode video ID
            on_disk: Whether transcript is on disk
        """
        if not self.connection:
            self.connect()

        self.connection.execute("""
            UPDATE episodes SET
                transcript_on_disk = ?,
                updated_at = ?
            WHERE video_id = ?
        """, [on_disk, format_timestamp(), video_id])

        logger.debug(f"Transcript on_disk flag set to {on_disk} for {video_id}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with stats
        """
        if not self.connection:
            self.connect()

        stats = {}

        # Total episodes
        result = self.connection.execute("SELECT COUNT(*) FROM episodes").fetchall()
        stats["total_episodes"] = result[0][0]

        # Episodes with transcripts
        result = self.connection.execute(
            "SELECT COUNT(*) FROM episodes WHERE transcript_md IS NOT NULL"
        ).fetchall()
        stats["episodes_with_transcripts"] = result[0][0]

        # Episodes with summaries
        result = self.connection.execute(
            "SELECT COUNT(*) FROM episodes WHERE summary_md IS NOT NULL"
        ).fetchall()
        stats["episodes_with_summaries"] = result[0][0]

        # Episodes by channel
        result = self.connection.execute(
            "SELECT channel_title, COUNT(*) FROM episodes GROUP BY channel_title ORDER BY COUNT(*) DESC"
        ).fetchall()
        stats["episodes_by_channel"] = {row[0]: row[1] for row in result}

        return stats
