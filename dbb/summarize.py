"""Ollama integration for local summarization."""

import logging
import json
import time
from typing import Optional
from pathlib import Path
import re

import requests

from dbb.config import Config
from dbb.utils import read_file, write_file, ensure_dir_exists, sanitize_filename

logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama API client for local LLM summarization."""

    def __init__(self, config: Config):
        """
        Initialize Ollama client.

        Args:
            config: Application configuration
        """
        self.config = config
        self.host = config.summarize.ollama_host
        self.model = config.summarize.ollama_model
        self.timeout = config.summarize.timeout_s
        self.retry_attempts = config.summarize.retry_attempts

        logger.info(f"Ollama client initialized: {self.host} / {self.model}")

    def check_health(self) -> bool:
        """
        Check if Ollama server is healthy.

        Returns:
            True if server is responding, False otherwise
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        Generate response from Ollama with retry logic.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Generated response or None if all retries fail
        """
        for attempt in range(self.retry_attempts):
            try:
                url = f"{self.host}/api/generate"

                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                }

                if system_prompt:
                    payload["system"] = system_prompt

                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )

                response.raise_for_status()
                data = response.json()
                generated_text = data.get("response", "")

                if generated_text:
                    logger.debug(f"Generated response from Ollama (attempt {attempt + 1})")
                    return generated_text

                logger.warning(f"Empty response from Ollama (attempt {attempt + 1}/{self.retry_attempts})")

            except requests.exceptions.Timeout:
                logger.warning(f"Ollama request timeout (attempt {attempt + 1}/{self.retry_attempts})")
                if attempt < self.retry_attempts - 1:
                    wait_time = 2 ** attempt
                    logger.debug(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

            except requests.RequestException as e:
                logger.error(f"Ollama request failed (attempt {attempt + 1}/{self.retry_attempts}): {e}")
                if attempt < self.retry_attempts - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)

            except json.JSONDecodeError as e:
                logger.error(f"Ollama response parsing failed: {e}")
                break

        logger.error(f"Failed to generate response after {self.retry_attempts} attempts")
        return None


class SummarizerManager:
    """Manages transcript summarization via Ollama."""

    def __init__(self, config: Config):
        """
        Initialize summarizer manager.

        Args:
            config: Application configuration
        """
        self.config = config
        self.ollama = OllamaClient(config)
        # Store default template for later use
        self.default_template = self._load_prompt_template(self.config.summarize.prompt_path)
        self.summary_dir = Path(config.summary_dir)
        ensure_dir_exists(self.summary_dir)
        # Cache for channel-specific prompts
        self._channel_prompts = {}

    def _load_prompt_template(self, prompt_path: str) -> str:
        """Load summary prompt template from file."""
        try:
            template = read_file(prompt_path)
            logger.info(f"Loaded prompt template from {prompt_path}")
            return template
        except FileNotFoundError:
            logger.warning(f"Prompt template not found at {prompt_path}, using default")
            return self._default_prompt_template()

    def _get_prompt_for_channel(self, channel_name: str) -> str:
        """
        Get the appropriate prompt template for a channel.

        Args:
            channel_name: Name of the YouTube channel

        Returns:
            Prompt template string
        """
        # Check if we have a cached version
        if channel_name in self._channel_prompts:
            return self._channel_prompts[channel_name]

        # Check if there's a channel-specific prompt configured
        if channel_name in self.config.summarize.channel_prompts:
            prompt_path = self.config.summarize.channel_prompts[channel_name]
            template = self._load_prompt_template(prompt_path)
            self._channel_prompts[channel_name] = template
            logger.info(f"Using channel-specific prompt for '{channel_name}'")
            return template

        # Fall back to default prompt
        logger.debug(f"No channel-specific prompt for '{channel_name}', using default")
        self._channel_prompts[channel_name] = self.default_template
        return self.default_template

    @staticmethod
    def _default_prompt_template() -> str:
        """Get default prompt template."""
        return """You are an expert podcast summary creator. Create a concise, well-structured markdown summary of the following podcast transcript.

The summary should include:
1. **Overview** - 2-3 sentence summary of the main topic
2. **Key Points** - 5-7 bullet points of the most important takeaways
3. **Speakers** - Brief description of who is speaking (if mentioned)
4. **Resources & Takeaways** - Any mentioned resources, links, or actionable items

Keep the summary concise but comprehensive. Use markdown formatting.

TRANSCRIPT:
{transcript}

SUMMARY:"""

    def summarize(self, transcript: str, channel_name: str = None) -> Optional[str]:
        """
        Summarize transcript using Ollama.

        Args:
            transcript: Full transcript text
            channel_name: Name of the YouTube channel (for channel-specific prompts)

        Returns:
            Markdown summary or None if generation fails
        """
        if not transcript or len(transcript.strip()) == 0:
            logger.warning("Empty transcript provided for summarization")
            return None

        # Truncate transcript if too long to fit in context
        max_context = 8000  # Approximate token limit
        if len(transcript) > max_context:
            logger.warning(f"Transcript too long ({len(transcript)} chars), truncating to {max_context}")
            transcript = transcript[:max_context] + "...\n[TRANSCRIPT TRUNCATED]"

        # Get appropriate prompt template for this channel
        if channel_name:
            prompt_template = self._get_prompt_for_channel(channel_name)
        else:
            prompt_template = self.default_template

        # Prepare prompt
        prompt = prompt_template.format(transcript=transcript)

        # Generate summary
        logger.info(f"Generating summary via Ollama{f' for channel: {channel_name}' if channel_name else ''}...")
        summary = self.ollama.generate(prompt)

        if summary:
            logger.info("Summary generated successfully")
            return self._clean_summary(summary)
        else:
            logger.error("Failed to generate summary")
            return None

    @staticmethod
    def _clean_summary(summary: str) -> str:
        """Clean up generated summary."""
        # Remove any leading/trailing whitespace
        summary = summary.strip()

        # Ensure it starts with markdown formatting
        if not summary.startswith("#"):
            # Add a basic header if missing
            lines = summary.split("\n")
            if lines:
                summary = f"# Summary\n\n{summary}"

        return summary

    def save_summary(self, video_id: str, summary: str, title: str) -> Path:
        """
        Save summary to local file.

        Args:
            video_id: YouTube video ID
            summary: Summary text
            title: Video title (for filename)

        Returns:
            Path to saved file
        """
        # Create filename from video_id and title
        safe_title = sanitize_filename(title)
        filename = f"{video_id}_{safe_title}.md"
        file_path = self.summary_dir / filename

        # Write file
        write_file(file_path, summary)
        logger.debug(f"Summary saved to {file_path}")

        return file_path
