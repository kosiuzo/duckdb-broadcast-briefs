"""Configuration management with Pydantic and environment variable support."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import yaml

logger = logging.getLogger(__name__)


class ChannelConfig(BaseModel):
    """YouTube channel configuration."""
    name: str = Field(..., description="Channel display name")
    channel_id: Optional[str] = Field(default=None, description="YouTube channel ID (for uploads)")
    playlist_id: Optional[str] = Field(default=None, description="YouTube playlist ID (for podcast episodes)")

    @field_validator("channel_id", "playlist_id", mode="before")
    @classmethod
    def validate_ids(cls, v):
        """Remove URL parameters from playlist IDs if present."""
        if v and "&" in str(v):
            return v.split("&")[0]
        return v

    def __init__(self, **data):
        """Validate that at least one ID is provided."""
        super().__init__(**data)
        if not self.channel_id and not self.playlist_id:
            raise ValueError("Must provide either channel_id or playlist_id")


class FetchConfig(BaseModel):
    """YouTube API fetch configuration."""
    use_youtube_api: bool = Field(default=True, description="Use YouTube Data API")
    api_key_env: str = Field(default="YOUTUBE_API_KEY", description="Environment variable for API key")
    max_per_channel: Optional[int] = Field(default=None, description="Max videos per channel (None = all)")


class TranscriptProviderConfig(BaseModel):
    """Individual transcript provider configuration."""
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    timeout_s: int = Field(default=30, description="Request timeout in seconds")
    enabled: bool = Field(default=True, description="Enable this provider")


class TranscriptsConfig(BaseModel):
    """Transcript providers configuration."""
    order: List[str] = Field(
        default=["supadata", "ytio", "socialkit", "youtube_transcript_api"],
        description="Order to try transcript providers"
    )
    min_chars: int = Field(default=400, description="Minimum transcript length (sanity check)")

    supadata: TranscriptProviderConfig = Field(default_factory=lambda: TranscriptProviderConfig(
        base_url="https://api.supadata.ai/v1/youtube/transcript",
        api_key_env="SUPADATA_API_KEY"
    ))
    ytio: TranscriptProviderConfig = Field(default_factory=lambda: TranscriptProviderConfig(
        base_url="https://www.youtube-transcript.io/api"
    ))
    socialkit: TranscriptProviderConfig = Field(default_factory=lambda: TranscriptProviderConfig(
        base_url="https://api.socialkit.dev/youtube-transcript",
        api_key_env="SOCIALKIT_API_KEY"
    ))
    youtube_transcript_api: TranscriptProviderConfig = Field(default_factory=lambda: TranscriptProviderConfig())


class SummarizeConfig(BaseModel):
    """Ollama summarization configuration."""
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama server host")
    ollama_model: str = Field(default="llama3.1:8b", description="Ollama model to use")
    prompt_path: str = Field(default="./prompts/default_prompt.md", description="Path to default summary prompt template")
    channel_prompts: Dict[str, str] = Field(
        default_factory=dict,
        description="Channel-specific prompt paths (key=channel_name, value=prompt_path)"
    )
    timeout_s: int = Field(default=300, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")


class EmailConfig(BaseModel):
    """Email digest configuration."""
    enabled: bool = Field(default=True, description="Enable email sending")
    from_name: str = Field(default="DBB Weekly", description="Sender display name")
    from_email: str = Field(default="", description="Sender email address")
    recipients: List[str] = Field(default_factory=list, description="Default email recipients for all channels")
    subject_format: str = Field(
        default="Your Weekly Podcast Digest ({{ start_date }} – {{ end_date }})",
        description="Email subject template"
    )
    channel_recipients: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Channel-specific email recipients (key=channel_name, value=list of emails)"
    )
    send_separate_emails: bool = Field(
        default=True,
        description="Send separate email for each channel instead of combined digest"
    )


class SmtpConfig(BaseModel):
    """SMTP email server configuration."""
    host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    port: int = Field(default=587, description="SMTP server port")
    use_tls: bool = Field(default=True, description="Use TLS for SMTP")
    username: str = Field(default="", description="SMTP username")
    password: str = Field(default="", description="SMTP password")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    format: str = Field(
        default="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        description="Log format"
    )


class Config(BaseModel):
    """Main application configuration."""
    db_path: str = Field(default="./dbb.duckdb", description="DuckDB database path")
    data_dir: str = Field(default="./data", description="Data directory")
    transcript_dir: str = Field(default="./data/transcripts", description="Transcripts storage directory")
    summary_dir: str = Field(default="./data/summaries", description="Summaries storage directory")

    channels: List[ChannelConfig] = Field(default_factory=list, description="YouTube channels to archive")
    fetch: FetchConfig = Field(default_factory=FetchConfig, description="YouTube fetch config")
    transcripts_providers: TranscriptsConfig = Field(default_factory=TranscriptsConfig, description="Transcript providers")
    summarize: SummarizeConfig = Field(default_factory=SummarizeConfig, description="Summarization config")
    email: EmailConfig = Field(default_factory=EmailConfig, description="Email config")
    smtp: SmtpConfig = Field(default_factory=SmtpConfig, description="SMTP config")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging config")

    @field_validator("channels", mode="before")
    @classmethod
    def validate_channels(cls, v):
        """Ensure at least one channel is configured."""
        if not v:
            logger.warning("No channels configured in config file")
        return v

    @staticmethod
    def _resolve_value(value: Any) -> Any:
        """Recursively resolve ${VAR} patterns to environment variables."""
        if isinstance(value, str):
            # Handle inline ${VAR} patterns anywhere in the string
            import re
            pattern = r'\$\{([^}]+)\}'

            def replace_var(match):
                env_var = match.group(1)
                resolved = os.getenv(env_var)
                if resolved is None:
                    logger.warning(f"Environment variable '{env_var}' not found, using empty string")
                    return ""
                return resolved

            return re.sub(pattern, replace_var, value)
        elif isinstance(value, dict):
            return {k: Config._resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [Config._resolve_value(v) for v in value]
        return value

    def resolve_env_vars(self) -> "Config":
        """Resolve environment variables in configuration."""
        # model_dump returns the already-set values, not the original string templates
        # We need to manually build a dict with the original string values for resolution
        config_dict = {}
        for field_name in Config.model_fields.keys():
            value = getattr(self, field_name)
            # For nested models, we still use model_dump to get the dict structure
            if hasattr(value, 'model_dump'):
                config_dict[field_name] = value.model_dump()
            else:
                config_dict[field_name] = value

        resolved_dict = self._resolve_value(config_dict)
        return Config(**resolved_dict)

    def get_api_key(self, env_var_name: str) -> str:
        """Get API key from environment variable."""
        key = os.getenv(env_var_name)
        if not key:
            logger.warning(f"API key environment variable '{env_var_name}' not set")
            return ""
        return key


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to config.yaml file. If None, looks for config.yaml in current directory.

    Returns:
        Config object with resolved environment variables
    """
    if config_path is None:
        config_path = "config.yaml"

    config_path = Path(config_path)

    # If config file doesn't exist, try config.yaml.example
    if not config_path.exists():
        example_path = config_path.parent / f"{config_path.name}.example"
        if example_path.exists():
            logger.warning(f"Config file not found at {config_path}, using {example_path}")
            config_path = example_path
        else:
            logger.error(f"Config file not found at {config_path}")
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load YAML
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f) or {}

    # Resolve environment variables BEFORE Pydantic validation
    resolved_data = Config._resolve_value(config_data)

    # Create config object with resolved data
    config = Config(**resolved_data)

    logger.info(f"Configuration loaded from {config_path}")
    return config


def setup_logging(config: Config):
    """Configure logging based on config."""
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper()),
        format=config.logging.format,
    )
    logger.info(f"Logging configured at level {config.logging.level}")
