"""YouTube API integration for fetching episode metadata."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dbb.config import Config

logger = logging.getLogger(__name__)


class YouTubeClient:
    """YouTube Data API client."""

    def __init__(self, config: Config):
        """
        Initialize YouTube client.

        Args:
            config: Application configuration
        """
        self.config = config
        self.api_key = config.get_api_key(config.fetch.api_key_env)
        if not self.api_key:
            raise ValueError(f"YouTube API key not found in {config.fetch.api_key_env}")

        self.service = build("youtube", "v3", developerKey=self.api_key)
        logger.info("YouTube API client initialized")

    def get_uploads_playlist_id(self, channel_id: str) -> Optional[str]:
        """
        Get uploads playlist ID for a channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Uploads playlist ID or None if error
        """
        try:
            request = self.service.channels().list(
                part="contentDetails",
                id=channel_id
            )
            response = request.execute()

            if not response.get("items"):
                logger.error(f"Channel not found: {channel_id}")
                return None

            uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            logger.debug(f"Uploads playlist for {channel_id}: {uploads_playlist_id}")
            return uploads_playlist_id

        except HttpError as e:
            logger.error(f"YouTube API error getting uploads playlist: {e}")
            return None

    def get_playlist_videos(self, playlist_id: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all videos from a playlist.

        Args:
            playlist_id: YouTube playlist ID
            max_results: Maximum number of results to return (None = all)

        Returns:
            List of video metadata dictionaries
        """
        videos = []
        skipped_private = 0
        next_page_token = None
        page_count = 0

        try:
            while True:
                request = self.service.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,  # Max allowed by API
                    pageToken=next_page_token
                )
                response = request.execute()

                for item in response.get("items", []):
                    snippet = item["snippet"]
                    video_id = snippet["resourceId"]["videoId"]
                    title = snippet["title"]

                    # Skip private videos
                    if title == "Private video":
                        logger.debug(f"Skipping private video: {video_id}")
                        skipped_private += 1
                        continue

                    video_data = {
                        "video_id": video_id,
                        "title": title,
                        "channel_id": snippet["channelId"],
                        "channel_title": snippet["channelTitle"],
                        "published_at": snippet["publishedAt"],
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    }
                    videos.append(video_data)

                    if max_results and len(videos) >= max_results:
                        logger.info(f"Reached max results limit ({max_results})")
                        return videos[:max_results]

                next_page_token = response.get("nextPageToken")
                page_count += 1

                if not next_page_token:
                    break

                logger.debug(f"Fetched page {page_count} ({len(videos)} total videos, {skipped_private} private skipped)")

            if skipped_private > 0:
                logger.info(f"Fetched {len(videos)} videos from playlist {playlist_id} (skipped {skipped_private} private video(s))")
            else:
                logger.info(f"Fetched {len(videos)} videos from playlist {playlist_id}")
            return videos

        except HttpError as e:
            logger.error(f"YouTube API error fetching playlist: {e}")
            return videos

    def fetch_channel_episodes(self, channel_id: str, channel_title: str, max_per_channel: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch all episodes from a channel.

        Args:
            channel_id: YouTube channel ID
            channel_title: Channel display name
            max_per_channel: Maximum videos to fetch (None = all)

        Returns:
            List of episode metadata dictionaries
        """
        logger.info(f"Fetching episodes from channel: {channel_title} ({channel_id})")

        # Get uploads playlist
        uploads_playlist_id = self.get_uploads_playlist_id(channel_id)
        if not uploads_playlist_id:
            return []

        # Get videos
        videos = self.get_playlist_videos(uploads_playlist_id, max_per_channel)

        logger.info(f"Fetched {len(videos)} episodes from {channel_title}")
        return videos

    def fetch_all_episodes(self) -> List[Dict[str, Any]]:
        """
        Fetch episodes from all configured channels or playlists.

        Returns:
            List of all episode metadata dictionaries
        """
        all_episodes = []

        for channel in self.config.channels:
            # If playlist_id is provided, fetch from playlist directly
            if channel.playlist_id:
                # Clean up playlist_id: remove &si=xxx tracking parameter
                clean_playlist_id = channel.playlist_id.split("&")[0]
                logger.info(f"Fetching episodes from playlist: {channel.name} ({clean_playlist_id})")
                episodes = self.get_playlist_videos(
                    clean_playlist_id,
                    self.config.fetch.max_per_channel
                )
            # Otherwise fetch from channel uploads
            elif channel.channel_id:
                episodes = self.fetch_channel_episodes(
                    channel.channel_id,
                    channel.name,
                    self.config.fetch.max_per_channel
                )
            else:
                logger.warning(f"Channel {channel.name} has neither channel_id nor playlist_id")
                continue

            all_episodes.extend(episodes)

        logger.info(f"Total episodes fetched: {len(all_episodes)}")
        return all_episodes
