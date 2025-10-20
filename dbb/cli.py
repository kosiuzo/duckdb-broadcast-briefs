"""Click CLI for DuckDB Broadcast Briefs."""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from dotenv import load_dotenv

from dbb.config import Config, load_config, setup_logging
from dbb.db import DatabaseManager
from dbb.youtube import YouTubeClient
from dbb.transcripts import TranscriptManager
from dbb.summarize import SummarizerManager
from dbb.digest import DigestRenderer, DigestSender, save_digest_previews
from dbb.utils import compute_sha256, delete_file, read_file

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)
console = Console()


@click.group()
@click.version_option()
def main():
    """DuckDB Broadcast Briefs - YouTube Podcast Archive System."""
    pass


@main.command()
@click.option("--config", default="config.yaml", help="Path to configuration file")
def initdb(config: str):
    """Initialize database with schema."""
    try:
        cfg = load_config(config)
        setup_logging(cfg)

        db = DatabaseManager(cfg)
        db.connect()

        with Progress() as progress:
            task = progress.add_task("[green]Initializing database...", total=2)

            db.init_schema()
            progress.update(task, advance=1)

            db.ensure_directories()
            progress.update(task, advance=1)

        console.print("[green]✓ Database initialized successfully[/green]")
        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception(e)
        sys.exit(1)


@main.command()
@click.option("--config", default="config.yaml", help="Path to configuration file")
def fetch(config: str):
    """Fetch episodes from YouTube channels."""
    try:
        cfg = load_config(config)
        setup_logging(cfg)

        console.print("[cyan]Starting episode fetch from YouTube...[/cyan]")

        # Initialize clients
        db = DatabaseManager(cfg)
        db.connect()
        yt = YouTubeClient(cfg)

        # Fetch episodes (handles both channel_id and playlist_id)
        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching episodes...", total=1)
            all_episodes = yt.fetch_all_episodes()
            progress.update(task, advance=1)

        # Insert into database
        inserted = 0
        skipped = 0

        with Progress() as progress:
            task = progress.add_task("[cyan]Inserting into database...", total=len(all_episodes))

            for episode in all_episodes:
                if db.insert_episode(episode):
                    inserted += 1
                else:
                    skipped += 1
                progress.update(task, advance=1)

        # Display results
        table = Table(title="Fetch Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_row("Total fetched", str(len(all_episodes)))
        table.add_row("Newly inserted", str(inserted))
        table.add_row("Already existed", str(skipped))
        console.print(table)

        db.close()
        console.print("[green]✓ Fetch complete[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception(e)
        sys.exit(1)


@main.command()
@click.option("--recent", default=10, help="Number of recent episodes to process")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def transcribe(recent: int, config: str):
    """Fetch transcripts for episodes."""
    try:
        cfg = load_config(config)
        setup_logging(cfg)

        console.print(f"[cyan]Fetching transcripts for {recent} recent episodes...[/cyan]")

        # Initialize clients
        db = DatabaseManager(cfg)
        db.connect()
        transcript_mgr = TranscriptManager(cfg)

        # Get episodes without transcripts
        episodes = db.get_episodes_without_transcript(recent)

        if not episodes:
            console.print("[yellow]No episodes need transcription[/yellow]")
            db.close()
            return

        # Process each episode
        success = 0
        failed = 0

        with Progress() as progress:
            task = progress.add_task("[cyan]Processing episodes...", total=len(episodes))

            for episode in episodes:
                video_id = episode["video_id"]
                title = episode["title"]

                try:
                    # Fetch transcript
                    transcript, provider, language = transcript_mgr.fetch_transcript(video_id, title)

                    if transcript:
                        # Save to file
                        file_path = transcript_mgr.save_transcript(video_id, transcript, title)

                        # Compute checksum and length
                        checksum = compute_sha256(transcript)
                        length = len(transcript)

                        # Update database
                        db.update_transcript(video_id, {
                            "transcript_md": transcript,
                            "provider": provider,
                            "language": language,
                            "checksum": checksum,
                            "length": length,
                            "path": str(file_path),
                            "on_disk": True,
                        })

                        success += 1
                    else:
                        failed += 1

                except Exception as e:
                    logger.error(f"Error processing {video_id}: {e}")
                    failed += 1

                progress.update(task, advance=1)

        # Display results
        table = Table(title="Transcription Results")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_row("Successful", str(success))
        table.add_row("Failed", str(failed))
        console.print(table)

        db.close()
        console.print("[green]✓ Transcription complete[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception(e)
        sys.exit(1)


@main.command()
@click.option("--recent", default=10, help="Number of recent episodes to process")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def summarize(recent: int, config: str):
    """Generate summaries for episodes with transcripts."""
    try:
        cfg = load_config(config)
        setup_logging(cfg)

        console.print(f"[cyan]Generating summaries for {recent} recent episodes...[/cyan]")

        # Initialize clients
        db = DatabaseManager(cfg)
        db.connect()
        summarizer = SummarizerManager(cfg)

        # Check Ollama health
        if not summarizer.ollama.check_health():
            console.print("[yellow]⚠ Warning: Ollama server not responding[/yellow]")

        # Get episodes without summaries
        episodes = db.get_episodes_without_summary(recent)

        if not episodes:
            console.print("[yellow]No episodes need summarization[/yellow]")
            db.close()
            return

        # Process each episode
        success = 0
        failed = 0

        with Progress() as progress:
            task = progress.add_task("[cyan]Processing episodes...", total=len(episodes))

            for episode in episodes:
                video_id = episode["video_id"]
                title = episode["title"]
                transcript = episode["transcript_md"]

                try:
                    # Generate summary
                    summary = summarizer.summarize(transcript)

                    if summary:
                        # Update database
                        db.update_summary(video_id, {
                            "summary_md": summary,
                            "model": cfg.summarize.ollama_model,
                        })
                        success += 1
                    else:
                        failed += 1

                except Exception as e:
                    logger.error(f"Error processing {video_id}: {e}")
                    failed += 1

                progress.update(task, advance=1)

        # Display results
        table = Table(title="Summarization Results")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_row("Successful", str(success))
        table.add_row("Failed", str(failed))
        console.print(table)

        db.close()
        console.print("[green]✓ Summarization complete[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception(e)
        sys.exit(1)


@main.command()
@click.option("--send", is_flag=True, help="Send email digest")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def digest(send: bool, config: str):
    """Generate weekly digest."""
    try:
        cfg = load_config(config)
        setup_logging(cfg)

        console.print("[cyan]Generating weekly digest...[/cyan]")

        # Initialize clients
        db = DatabaseManager(cfg)
        db.connect()

        # Get recent summaries
        episodes = db.get_recent_summaries(days=7)

        if not episodes:
            console.print("[yellow]No episodes from the past 7 days[/yellow]")
            db.close()
            return

        console.print(f"Found {len(episodes)} episodes from past 7 days")

        # Render digest
        renderer = DigestRenderer(cfg)
        now = datetime.now()
        start_date = now - timedelta(days=7)
        date_range = (start_date, now)

        html_content, text_content = renderer.render_digest(episodes, date_range)

        # Save previews
        save_digest_previews(html_content, text_content)
        console.print("[green]✓ Digest previews saved[/green]")

        # Send email if requested
        if send:
            sender = DigestSender(cfg)
            subject = f"Your Weekly Podcast Digest ({start_date.strftime('%Y-%m-%d')} – {now.strftime('%Y-%m-%d')})"
            if sender.send_digest(html_content, text_content, subject):
                console.print("[green]✓ Digest sent via email[/green]")
            else:
                console.print("[yellow]⚠ Failed to send digest (see logs)[/yellow]")

        db.close()
        console.print("[green]✓ Digest generation complete[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception(e)
        sys.exit(1)


@main.command()
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without actually deleting")
@click.option("--config", default="config.yaml", help="Path to configuration file")
def purgе(dry_run: bool, config: str):
    """Purge transcript files (DB retains full transcripts)."""
    try:
        cfg = load_config(config)
        setup_logging(cfg)

        console.print("[cyan]Purging transcript files...[/cyan]")

        # Initialize clients
        db = DatabaseManager(cfg)
        db.connect()

        # Get episodes with transcripts on disk
        episodes = db.get_episodes_with_transcript_on_disk()

        if not episodes:
            console.print("[yellow]No transcripts to purge[/yellow]")
            db.close()
            return

        # Process each episode
        deleted = 0
        failed = 0
        mismatched = 0

        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files...", total=len(episodes))

            for episode in episodes:
                video_id = episode["video_id"]
                transcript_path = Path(episode["transcript_path"])
                stored_checksum = episode["transcript_checksum"]

                try:
                    if not transcript_path.exists():
                        logger.warning(f"File not found: {transcript_path}")
                        db.set_transcript_on_disk(video_id, False)
                        failed += 1
                        progress.update(task, advance=1)
                        continue

                    # Verify checksum
                    from dbb.utils import compute_file_sha256
                    file_checksum = compute_file_sha256(transcript_path)

                    if file_checksum != stored_checksum:
                        logger.error(f"Checksum mismatch for {video_id}: expected {stored_checksum}, got {file_checksum}")
                        mismatched += 1
                        progress.update(task, advance=1)
                        continue

                    # Delete file
                    if not dry_run:
                        if delete_file(transcript_path):
                            db.set_transcript_on_disk(video_id, False)
                            deleted += 1
                        else:
                            failed += 1
                    else:
                        console.print(f"[dim]Would delete: {transcript_path}[/dim]")
                        deleted += 1

                except Exception as e:
                    logger.error(f"Error processing {video_id}: {e}")
                    failed += 1

                progress.update(task, advance=1)

        # Display results
        table = Table(title="Purge Results")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="magenta")
        if dry_run:
            table.add_row("Would delete", str(deleted))
        else:
            table.add_row("Deleted", str(deleted))
        table.add_row("Checksum mismatches", str(mismatched))
        table.add_row("Errors", str(failed))
        console.print(table)

        db.close()
        console.print("[green]✓ Purge complete[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception(e)
        sys.exit(1)


@main.command()
@click.option("--config", default="config.yaml", help="Path to configuration file")
def status(config: str):
    """Show database statistics."""
    try:
        cfg = load_config(config)
        setup_logging(cfg)

        # Initialize database
        db = DatabaseManager(cfg)
        db.connect()

        # Get stats
        stats = db.get_stats()

        # Display results
        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total episodes", str(stats["total_episodes"]))
        table.add_row("With transcripts", str(stats["episodes_with_transcripts"]))
        table.add_row("With summaries", str(stats["episodes_with_summaries"]))

        console.print(table)

        # Channel breakdown
        if stats["episodes_by_channel"]:
            channel_table = Table(title="Episodes by Channel")
            channel_table.add_column("Channel", style="cyan")
            channel_table.add_column("Count", style="magenta")

            for channel, count in stats["episodes_by_channel"].items():
                channel_table.add_row(channel, str(count))

            console.print(channel_table)

        db.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
