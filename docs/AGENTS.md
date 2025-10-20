# AI Agents & Advanced Features Guide

This document describes how to use AI agents and advanced features with DuckDB Broadcast Briefs.

## Overview

DuckDB Broadcast Briefs is designed to work with AI agents and automation tools for intelligent podcast management and analysis.

## Use Cases for AI Integration

### 1. Automatic Channel Discovery

Use AI to suggest new podcast channels based on episode summaries:

```python
from dbb.config import load_config
from dbb.db import DatabaseManager
import requests

def suggest_channels(config):
    """Use Claude to suggest new channels based on existing content."""
    db = DatabaseManager(config)
    db.connect()

    stats = db.get_stats()
    topics = db.connection.execute(
        "SELECT DISTINCT channel_title FROM episodes LIMIT 10"
    ).fetchall()

    prompt = f"""Based on these podcast channels: {topics}
    Suggest 5 similar podcast channels that would complement this collection.
    Return as JSON with channel names and YouTube channel IDs."""

    # Call your AI API here
    # response = ai_client.complete(prompt)
```

### 2. Automated Tagging

Use AI to tag episodes with topics:

```python
def auto_tag_episodes(config):
    """Use AI to tag episodes with relevant topics."""
    db = DatabaseManager(config)
    db.connect()

    episodes = db.connection.execute(
        "SELECT video_id, title, summary_md FROM episodes WHERE summary_md IS NOT NULL LIMIT 100"
    ).fetchall()

    for video_id, title, summary in episodes:
        prompt = f"""Analyze this podcast episode and identify 3-5 tags:
        Title: {title}
        Summary: {summary[:500]}

        Return JSON: {{"tags": ["tag1", "tag2", ...]}}"""

        # Call AI and store tags in DB
```

### 3. Intelligent Digest Summarization

Use AI to create ultra-condensed digest summaries:

```python
def create_ai_digest_summary(config):
    """Create an AI-powered executive summary of the week's episodes."""
    db = DatabaseManager(config)
    db.connect()

    episodes = db.get_recent_summaries(days=7)

    summaries_text = "\n\n".join([
        f"**{ep['title']}**\n{ep['summary_md'][:200]}..."
        for ep in episodes
    ])

    prompt = f"""Create a 200-word executive summary of this week's podcast highlights:

{summaries_text}

Focus on the most actionable insights and novel ideas."""

    # Call AI to generate summary
    # Send as email or append to digest
```

### 4. Cross-Episode Analysis

Use AI to find connections between episodes:

```python
def find_episode_connections(config, video_id1: str, video_id2: str):
    """Find thematic connections between two episodes."""
    db = DatabaseManager(config)
    db.connect()

    ep1 = db.connection.execute(
        "SELECT title, summary_md FROM episodes WHERE video_id = ?",
        [video_id1]
    ).fetchall()[0]

    ep2 = db.connection.execute(
        "SELECT title, summary_md FROM episodes WHERE video_id = ?",
        [video_id2]
    ).fetchall()[0]

    prompt = f"""Find thematic connections between these two podcast episodes:

Episode 1: {ep1[0]}
Summary: {ep1[1][:300]}

Episode 2: {ep2[0]}
Summary: {ep2[1][:300]}

Identify common themes, contradictions, or complementary ideas."""
```

### 5. Automated Fact-Checking

Use AI to flag potentially incorrect claims:

```python
def flag_claims_for_review(config):
    """Use AI to identify claims in episodes that might need fact-checking."""
    db = DatabaseManager(config)
    db.connect()

    episodes = db.connection.execute(
        "SELECT video_id, title, transcript_md FROM episodes WHERE transcript_md IS NOT NULL LIMIT 50"
    ).fetchall()

    for video_id, title, transcript in episodes:
        prompt = f"""Review this podcast episode transcript for factual claims that warrant fact-checking.

Title: {title}
Transcript excerpt: {transcript[:1000]}

Identify specific, verifiable claims that should be fact-checked.
Format: List of claims with timestamps if available."""
```

## Scripting Examples

### Example 1: Weekly Summary Report

Create an automated weekly report showing trends:

```python
#!/usr/bin/env python3
"""Generate weekly summary report."""

import sys
from datetime import datetime, timedelta
from dbb.config import load_config
from dbb.db import DatabaseManager

def main():
    config = load_config()
    db = DatabaseManager(config)
    db.connect()

    # Get stats for the past week
    week_ago = datetime.now() - timedelta(days=7)

    summaries = db.connection.execute("""
        SELECT COUNT(*) as count, channel_title FROM episodes
        WHERE summary_created_at >= ?
        GROUP BY channel_title
        ORDER BY count DESC
    """, [week_ago.isoformat()]).fetchall()

    print("📊 Weekly Summary Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    total = sum(row[0] for row in summaries)
    print(f"Total summaries created: {total}\n")

    print("By Channel:")
    for count, channel in summaries:
        print(f"  - {channel}: {count} episodes")

    db.close()

if __name__ == "__main__":
    main()
```

### Example 2: Batch Transcript Export

Export all transcripts for external analysis:

```python
#!/usr/bin/env python3
"""Export all transcripts to markdown files."""

import sys
from pathlib import Path
from dbb.config import load_config
from dbb.db import DatabaseManager

def main():
    config = load_config()
    db = DatabaseManager(config)
    db.connect()

    export_dir = Path("transcript_export")
    export_dir.mkdir(exist_ok=True)

    episodes = db.connection.execute("""
        SELECT video_id, title, channel_title, transcript_md
        FROM episodes
        WHERE transcript_md IS NOT NULL
    """).fetchall()

    for video_id, title, channel, transcript in episodes:
        # Create channel subdirectory
        channel_dir = export_dir / channel.replace(" ", "_")
        channel_dir.mkdir(exist_ok=True)

        # Write file
        filename = f"{video_id}_{title[:50].replace('/', '_')}.md"
        filepath = channel_dir / filename

        with open(filepath, "w") as f:
            f.write(f"# {title}\n\n")
            f.write(f"Video ID: {video_id}\n")
            f.write(f"Channel: {channel}\n\n")
            f.write(f"## Transcript\n\n{transcript}")

        print(f"Exported: {filepath}")

    db.close()
    print(f"\nExported {len(episodes)} transcripts to {export_dir}")

if __name__ == "__main__":
    main()
```

### Example 3: Content Gap Analysis

Find which topics/channels are underrepresented:

```python
#!/usr/bin/env python3
"""Analyze content gaps in your podcast archive."""

from dbb.config import load_config
from dbb.db import DatabaseManager

def main():
    config = load_config()
    db = DatabaseManager(config)
    db.connect()

    # Get episodes by channel over time
    episodes_by_channel = db.connection.execute("""
        SELECT
            channel_title,
            COUNT(*) as total,
            COUNT(CASE WHEN transcript_md IS NOT NULL THEN 1 END) as with_transcript,
            COUNT(CASE WHEN summary_md IS NOT NULL THEN 1 END) as with_summary
        FROM episodes
        GROUP BY channel_title
        ORDER BY total DESC
    """).fetchall()

    print("📋 Content Gap Analysis\n")
    print(f"{'Channel':<30} {'Total':<8} {'Transcript':<12} {'Summary':<10} {'Progress'}")
    print("-" * 70)

    for channel, total, transcript_count, summary_count in episodes_by_channel:
        transcript_pct = (transcript_count / total * 100) if total > 0 else 0
        summary_pct = (summary_count / total * 100) if total > 0 else 0

        progress_bar = "█" * int(summary_pct / 10) + "░" * (10 - int(summary_pct / 10))

        print(f"{channel:<30} {total:<8} {transcript_count}/{total:<8} {summary_count}/{total:<6} {progress_bar}")

    db.close()

if __name__ == "__main__":
    main()
```

## Integration with Automation Tools

### Zapier/Make Integration

Create webhooks to trigger actions:

```python
from flask import Flask, request
from dbb.config import load_config
from dbb.cli import fetch, transcribe, summarize, digest

app = Flask(__name__)

@app.route('/webhook/fetch', methods=['POST'])
def webhook_fetch():
    """Webhook to trigger fetch from Zapier."""
    try:
        config = load_config()
        # Call fetch logic
        return {"status": "success"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/webhook/digest', methods=['POST'])
def webhook_digest():
    """Webhook to trigger digest from Make."""
    try:
        config = load_config()
        # Call digest logic
        return {"status": "success"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(port=5000)
```

### Cron Job Scheduling

Add to your crontab:

```bash
# Every 6 hours - fetch new episodes
0 */6 * * * cd /path/to/dbb && /usr/bin/python3 -m dbb.cli fetch

# Every 12 hours - transcribe and summarize
0 */12 * * * cd /path/to/dbb && /usr/bin/python3 -m dbb.cli transcribe --recent 50 && /usr/bin/python3 -m dbb.cli summarize --recent 50

# Every Sunday at 9 AM - send digest
0 9 * * 0 cd /path/to/dbb && /usr/bin/python3 -m dbb.cli digest --send
```

### GitHub Actions Workflow

Create `.github/workflows/dbb-sync.yml`:

```yaml
name: DBB Sync

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Fetch episodes
        env:
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
        run: python -m dbb.cli fetch

      - name: Transcribe & Summarize
        env:
          SUPADATA_API_KEY: ${{ secrets.SUPADATA_API_KEY }}
          OLLAMA_HOST: ${{ secrets.OLLAMA_HOST }}
        run: |
          python -m dbb.cli transcribe --recent 50
          python -m dbb.cli summarize --recent 50

      - name: Send digest (Sundays only)
        if: github.event.schedule == '0 9 * * 0'
        env:
          SMTP_USERNAME: ${{ secrets.SMTP_USERNAME }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
        run: python -m dbb.cli digest --send

      - name: Commit changes
        run: |
          git config user.name "DBB Bot"
          git config user.email "bot@example.com"
          git add dbb.duckdb
          git commit -m "chore: update podcast archive" || true
          git push
```

## API Query Examples

### Query Recent Episodes

```python
from dbb.config import load_config
from dbb.db import DatabaseManager
from datetime import datetime, timedelta

config = load_config()
db = DatabaseManager(config)
db.connect()

# Episodes from past 7 days with summaries
recent = db.connection.execute("""
    SELECT
        video_id,
        title,
        channel_title,
        url,
        published_at,
        summary_md
    FROM episodes
    WHERE summary_created_at >= NOW() - INTERVAL 7 DAY
    ORDER BY published_at DESC
""").fetchall()

for ep in recent:
    print(f"{ep[1]} ({ep[2]})")
    print(f"  URL: {ep[3]}")
    print(f"  Summary: {ep[5][:100]}...")
```

### Search Episodes

```python
# Find episodes about a topic
results = db.connection.execute("""
    SELECT title, summary_md FROM episodes
    WHERE title ILIKE ? OR summary_md ILIKE ?
""", ['%artificial intelligence%', '%artificial intelligence%']).fetchall()

for title, summary in results:
    print(f"Found: {title}")
    print(f"  {summary[:150]}...")
```

### Analyze Topics Over Time

```python
# Get episode counts by channel over time
trends = db.connection.execute("""
    SELECT
        DATE_TRUNC('week', published_at) as week,
        channel_title,
        COUNT(*) as episode_count
    FROM episodes
    WHERE published_at IS NOT NULL
    GROUP BY DATE_TRUNC('week', published_at), channel_title
    ORDER BY week DESC
""").fetchall()

for week, channel, count in trends:
    print(f"{week}: {channel} - {count} episodes")
```

## Extending with Custom Agents

### Create a Custom Agent

```python
"""Custom AI agent for podcast analysis."""

from abc import ABC, abstractmethod
from dbb.config import Config
from dbb.db import DatabaseManager

class PodcastAgent(ABC):
    """Base class for podcast AI agents."""

    def __init__(self, config: Config):
        self.config = config
        self.db = DatabaseManager(config)
        self.db.connect()

    @abstractmethod
    def analyze(self):
        """Run analysis."""
        pass

    def cleanup(self):
        self.db.close()


class TrendAnalysisAgent(PodcastAgent):
    """Analyzes trends in podcast episodes."""

    def analyze(self):
        """Find trending topics."""
        episodes = self.db.connection.execute("""
            SELECT title, summary_md FROM episodes
            WHERE summary_created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """).fetchall()

        # Your AI analysis here
        print(f"Analyzed {len(episodes)} recent episodes")


class RecommendationAgent(PodcastAgent):
    """Recommends episodes based on topics."""

    def recommend(self, topic: str) -> list:
        """Find similar episodes."""
        results = self.db.connection.execute("""
            SELECT video_id, title, summary_md FROM episodes
            WHERE summary_md ILIKE ?
        """, [f'%{topic}%']).fetchall()

        return results
```

## Best Practices

1. **Always Use Context Managers**: Use `with` statements for database connections
2. **Error Handling**: Always wrap API calls in try-except blocks
3. **Logging**: Use Python's logging module for debugging
4. **Idempotency**: Design scripts to be safe to re-run
5. **Testing**: Test scripts against a copy of your database first
6. **Backups**: Backup your database before running batch operations

## Support & Resources

- **Documentation**: See README.md for full documentation
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Ask questions on GitHub Discussions
- **Source Code**: See `dbb/` directory for implementation details

---

**Remember**: All data is local and private. Use these AI integration examples responsibly and ethically.
