"""Transcript fetching with multi-provider failover."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional
import json

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from dbb.config import Config, TranscriptProviderConfig
from dbb.utils import compute_sha256, write_file, ensure_dir_exists

logger = logging.getLogger(__name__)


class TranscriptUnavailableError(Exception):
    """Raised when transcript cannot be fetched from a provider."""
    pass


class TranscriptProvider(ABC):
    """Abstract base class for transcript providers."""

    def __init__(self, config: TranscriptProviderConfig):
        """
        Initialize provider.

        Args:
            config: Provider configuration
        """
        self.config = config

    @abstractmethod
    def fetch(self, video_id: str) -> Tuple[str, str]:
        """
        Fetch transcript for video.

        Args:
            video_id: YouTube video ID

        Returns:
            Tuple of (transcript_text, language)

        Raises:
            TranscriptUnavailableError: If transcript cannot be fetched
        """
        pass


class SupadataProvider(TranscriptProvider):
    """Supadata transcript provider."""

    def fetch(self, video_id: str) -> Tuple[str, str]:
        """Fetch from Supadata."""
        if not self.config.enabled:
            raise TranscriptUnavailableError("Supadata provider disabled")

        api_key = self.config.api_key_env and self._get_api_key()
        if not api_key:
            raise TranscriptUnavailableError("Supadata API key not configured")

        try:
            url = f"{self.config.base_url}?video_id={video_id}"
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=self.config.timeout_s)
            response.raise_for_status()

            data = response.json()
            transcript = data.get("transcript", "")
            language = data.get("language", "en")

            if not transcript:
                raise TranscriptUnavailableError("Supadata returned empty transcript")

            logger.debug(f"Fetched transcript from Supadata for {video_id}")
            return transcript, language

        except requests.RequestException as e:
            raise TranscriptUnavailableError(f"Supadata request failed: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            raise TranscriptUnavailableError(f"Supadata response parse error: {e}")

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os
        if self.config.api_key_env:
            return os.getenv(self.config.api_key_env, "")
        return ""


class YouTubeTranscriptIOProvider(TranscriptProvider):
    """YouTube-transcript.io provider."""

    def fetch(self, video_id: str) -> Tuple[str, str]:
        """Fetch from YouTube-transcript.io."""
        if not self.config.enabled:
            raise TranscriptUnavailableError("YouTube-transcript.io provider disabled")

        try:
            url = f"{self.config.base_url}/transcript"
            params = {"videoId": video_id}
            response = requests.get(url, params=params, timeout=self.config.timeout_s)
            response.raise_for_status()

            data = response.json()

            # Response format: list of objects with "text" field
            if isinstance(data, list):
                transcript = " ".join([item.get("text", "") for item in data])
            else:
                transcript = data.get("transcript", "")

            if not transcript:
                raise TranscriptUnavailableError("YouTube-transcript.io returned empty transcript")

            logger.debug(f"Fetched transcript from YouTube-transcript.io for {video_id}")
            return transcript, "en"

        except requests.RequestException as e:
            raise TranscriptUnavailableError(f"YouTube-transcript.io request failed: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            raise TranscriptUnavailableError(f"YouTube-transcript.io response parse error: {e}")


class SocialKitProvider(TranscriptProvider):
    """SocialKit transcript provider."""

    def fetch(self, video_id: str) -> Tuple[str, str]:
        """Fetch from SocialKit."""
        if not self.config.enabled:
            raise TranscriptUnavailableError("SocialKit provider disabled")

        api_key = self.config.api_key_env and self._get_api_key()
        if not api_key:
            raise TranscriptUnavailableError("SocialKit API key not configured")

        try:
            url = f"{self.config.base_url}?video_id={video_id}"
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=self.config.timeout_s)
            response.raise_for_status()

            data = response.json()
            transcript = data.get("transcript", "")
            language = data.get("language", "en")

            if not transcript:
                raise TranscriptUnavailableError("SocialKit returned empty transcript")

            logger.debug(f"Fetched transcript from SocialKit for {video_id}")
            return transcript, language

        except requests.RequestException as e:
            raise TranscriptUnavailableError(f"SocialKit request failed: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            raise TranscriptUnavailableError(f"SocialKit response parse error: {e}")

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os
        if self.config.api_key_env:
            return os.getenv(self.config.api_key_env, "")
        return ""


class YouTubeTranscriptAPIProvider(TranscriptProvider):
    """youtube-transcript-api fallback provider."""

    def fetch(self, video_id: str) -> Tuple[str, str]:
        """Fetch from youtube-transcript-api."""
        if not self.config.enabled:
            raise TranscriptUnavailableError("youtube-transcript-api provider disabled")

        try:
            # Extract languages list from config
            languages = ["en"]
            if hasattr(self.config, 'languages') and self.config.languages:
                languages = self.config.languages

            # Use the newer API: create instance and call fetch()
            api = YouTubeTranscriptApi()
            transcript_list = api.fetch(video_id, languages=languages)

            # Convert to text format
            if isinstance(transcript_list, list):
                # If it returns a list of dicts with 'text' field
                transcript = " ".join([item.get("text", "") for item in transcript_list])
            else:
                # If it returns a FetchedTranscript object, format it
                formatter = TextFormatter()
                transcript = formatter.format_transcript(transcript_list)

            if not transcript:
                raise TranscriptUnavailableError("youtube-transcript-api returned empty transcript")

            logger.debug(f"Fetched transcript from youtube-transcript-api for {video_id}")
            return transcript, languages[0] if languages else "en"

        except Exception as e:
            raise TranscriptUnavailableError(f"youtube-transcript-api failed: {e}")


class TranscriptManager:
    """Manages transcript fetching with provider failover."""

    def __init__(self, config: Config):
        """
        Initialize transcript manager.

        Args:
            config: Application configuration
        """
        self.config = config
        self.transcript_dir = Path(config.transcript_dir)
        ensure_dir_exists(self.transcript_dir)

        # Initialize providers
        self.providers = {
            "supadata": SupadataProvider(config.transcripts_providers.supadata),
            "ytio": YouTubeTranscriptIOProvider(config.transcripts_providers.ytio),
            "socialkit": SocialKitProvider(config.transcripts_providers.socialkit),
            "youtube_transcript_api": YouTubeTranscriptAPIProvider(config.transcripts_providers.youtube_transcript_api),
        }

    def fetch_transcript(self, video_id: str, title: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Fetch transcript with provider failover.

        Args:
            video_id: YouTube video ID
            title: Video title (for logging)

        Returns:
            Tuple of (transcript_text, provider_name, language) or (None, None, None) if all fail
        """
        min_chars = self.config.transcripts_providers.min_chars
        provider_order = self.config.transcripts_providers.order

        for provider_name in provider_order:
            if provider_name not in self.providers:
                logger.warning(f"Unknown provider: {provider_name}")
                continue

            provider = self.providers[provider_name]

            try:
                transcript, language = provider.fetch(video_id)

                # Sanity check: minimum length
                if len(transcript) < min_chars:
                    logger.warning(
                        f"Transcript from {provider_name} too short ({len(transcript)} < {min_chars}), trying next provider"
                    )
                    continue

                logger.info(f"Successfully fetched transcript from {provider_name} for {video_id}")
                return transcript, provider_name, language

            except TranscriptUnavailableError as e:
                logger.debug(f"Provider {provider_name} failed for {video_id}: {e}")
                continue

        logger.warning(f"All transcript providers failed for {video_id} ({title})")
        return None, None, None

    def save_transcript(self, video_id: str, transcript: str, title: str) -> Path:
        """
        Save transcript to local file.

        Args:
            video_id: YouTube video ID
            transcript: Transcript text
            title: Video title (for filename)

        Returns:
            Path to saved file
        """
        from dbb.utils import sanitize_filename

        # Create filename from video_id and title
        safe_title = sanitize_filename(title)
        filename = f"{video_id}_{safe_title}.md"
        file_path = self.transcript_dir / filename

        # Write file
        write_file(file_path, transcript)
        logger.debug(f"Transcript saved to {file_path}")

        return file_path
