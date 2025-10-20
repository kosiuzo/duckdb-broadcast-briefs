# DuckDB Broadcast Briefs

**Stay current on long-form YouTube podcasts via a weekly email digest. Build a local, queryable archive of all episodes with full transcripts and concise summaries.**

A private-first, open-source tool for archiving YouTube podcast episodes with:
- 📺 **Episode Fetching** - Automatically fetch latest episodes from your favorite channels
- 📝 **Multi-Provider Transcription** - API-based transcripts with intelligent failover (Supadata → YouTube-transcript.io → SocialKit → youtube-transcript-api)
- 🤖 **Local Summarization** - Generate summaries locally via Ollama (no cloud LLMs)
- 📧 **Weekly Digests** - Beautiful HTML email digests grouped by channel
- 💾 **Queryable Archive** - DuckDB for fast local search and analysis

## Features

✅ **Idempotent Operations** - Every command is safe to re-run
✅ **Database as Source of Truth** - All transcripts stored in DuckDB
✅ **No Audio Downloads** - Transcripts via APIs only
✅ **Privacy-First** - Everything runs locally, no cloud dependencies
✅ **Multi-Provider Failover** - Automatic fallback between transcript sources
✅ **Beautiful Digests** - HTML emails with CSS inlining, grouped by channel
✅ **Easy Setup** - YAML configuration, environment variables, sensible defaults

## Quick Start

### 1. Installation

**Requirements**: (Python 3.10+ recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/duckdb-broadcast-briefs.git
cd duckdb-broadcast-briefs

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Or install dependencies only
pip install -r requirements.txt
```

**Important**: Always activate the virtual environment before running commands:
```bash
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### 2. Configuration

Copy the example files:

```bash
cp .env.example .env
cp config.yaml.example config.yaml
```

**Edit `config.yaml` with your YouTube channels or podcast playlists:**

For best results with transcripts, use **podcast playlist IDs** instead of channel IDs. This ensures you only fetch actual podcast episodes with captions.

```yaml
channels:
  - name: "Lex Fridman Podcast"
    playlist_id: "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
  - name: "Joe Rogan Experience"
    playlist_id: "PLrAXtmErZgOdic8HjG-yveLOVYOKwJdvV"
```

### Finding Podcast Playlist IDs

1. Go to the creator's YouTube channel (e.g., https://www.youtube.com/@lexfridman)
2. Click on the **"Playlists"** tab
3. Find the official podcast/show playlist (e.g., "Lex Fridman Podcast")
4. Click on it to open the playlist
5. The URL will be: `https://www.youtube.com/playlist?list=PLxxxxxxxxxxxx`
6. Copy the `list=` parameter (e.g., `PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf`)

Alternatively, you can still use `channel_id` to fetch all uploads:

```yaml
channels:
  - name: "My Channel"
    channel_id: "UCxxxxxxxxxxxxx"
```

**Edit `.env` with your API keys:**

```bash
YOUTUBE_API_KEY=your_api_key_here
SUPADATA_API_KEY=optional_api_key
SOCIALKIT_API_KEY=optional_api_key
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 3. Initialize Database

```bash
dbb initdb
```

This creates:
- DuckDB database at `./dbb.duckdb`
- Directories: `data/transcripts/`, `data/summaries/`

### 4. Fetch Episodes

**Activate your virtual environment first:**
```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# Then run fetch:
dbb fetch
```

Fetches latest episodes from all configured channels.

### 5. Get Transcripts

```bash
dbb transcribe --recent 10
```

Fetches transcripts for the 10 most recent episodes without transcripts.

### 6. Generate Summaries

First, ensure Ollama is running:

```bash
ollama serve  # In another terminal
```

Then generate summaries:

```bash
dbb summarize --recent 10
```

### 7. Generate Weekly Digest

```bash
dbb digest --send
```

Generates and sends (optional `--send`) a beautiful HTML digest of episodes summarized in the past 7 days.

## API Setup Guide

### YouTube Data API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "YouTube Data API v3"
4. Create an API key (Credentials → Create Credentials → API Key)
5. Add key to `.env`:
   ```bash
   YOUTUBE_API_KEY=your_key_here
   ```

**Cost**: Free tier includes 10,000 units/day. Each `fetch` operation uses ~1-2 units per 50 videos.

### Transcript Providers

#### Option 1: Supadata (Recommended)
- Website: https://supadata.ai
- Sign up and get API key
- Add to `.env`: `SUPADATA_API_KEY=your_key`
- ~$50-200/month depending on usage

#### Option 2: YouTube-transcript.io (Free)
- Website: https://youtube-transcript.io
- Free tier available, no API key required
- No setup needed - works out of the box

#### Option 3: SocialKit
- Website: https://socialkit.dev
- Sign up for API access
- Add to `.env`: `SOCIALKIT_API_KEY=your_key`

#### Option 4: youtube-transcript-api (Fallback)
- Open source Python library
- No API key required
- Automatically used as last resort
- Less reliable, sometimes blocked

**Recommended Setup**: Use free providers first (YouTube-transcript.io), with Supadata as backup.

### Ollama Setup

1. Install Ollama: https://ollama.ai
2. Download a model:
   ```bash
   ollama pull llama3.1:8b  # ~7.5GB
   ```
3. Start Ollama:
   ```bash
   ollama serve
   ```
4. Verify in another terminal:
   ```bash
   curl http://localhost:11434/api/tags
   ```

**Models**: llama2, llama3.1, mistral, neural-chat, etc.

### Email Setup (Gmail)

1. Enable 2-factor authentication on your Gmail account
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Add to `.env`:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password  # NOT your regular Gmail password
   ```
4. In `config.yaml`:
   ```yaml
   email:
     enabled: true
     from_name: "DBB Weekly"
     from_email: "your_email@gmail.com"
     recipients:
       - "recipient@example.com"
   ```

## CLI Commands

**Before running any commands, make sure your virtual environment is activated:**
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Then run any dbb command:
dbb initdb
dbb fetch
dbb transcribe
# etc...
```

### Global Options

All commands support:
- `--help` - Show help message and exit
- `--config TEXT` - Path to configuration file (default: `config.yaml`)

### `dbb initdb`
Initialize database with schema and directories.

**Purpose**: Set up the database and required directories before first use. Must be run before other commands.

**Usage**:
```bash
dbb initdb
dbb initdb --config /path/to/config.yaml
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | TEXT | `config.yaml` | Path to configuration file |

**Output**:
- Creates DuckDB database at configured path (default: `./dbb.duckdb`)
- Creates directories: `data/transcripts/`, `data/summaries/`
- Initializes episodes table with schema and indexes

**Example**:
```bash
# Initialize with default config
dbb initdb

# Initialize with custom config
dbb initdb --config production.yaml
```

---

### `dbb fetch`
Fetch latest episodes from all configured channels or playlists.

**Purpose**: Query YouTube Data API and fetch new episodes. Idempotent - safe to run multiple times.

**Usage**:
```bash
dbb fetch
dbb fetch --config config.yaml
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | TEXT | `config.yaml` | Path to configuration file |

**Fetches**:
- All configured channels or playlists from `config.yaml`
- Respects `max_per_channel` setting for API quota management
- Skips episodes already in database (idempotent)

**Example**:
```bash
# Fetch from all configured channels
dbb fetch

# Fetch with custom config file
dbb fetch --config ~/configs/production.yaml

# Fetch and check status (then run)
dbb fetch && dbb status
```

---

### `dbb transcribe`
Fetch transcripts for episodes without transcripts.

**Purpose**: Query configured transcript providers in order (failover chain). Tries providers until one succeeds.

**Usage**:
```bash
dbb transcribe --recent 10
dbb transcribe --recent 5 --config config.yaml
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--recent` | INTEGER | `10` | Number of most recent episodes without transcripts to process |
| `--config` | TEXT | `config.yaml` | Path to configuration file |

**Provider Failover Chain** (configured in `config.yaml`):
1. Supadata (paid, most reliable)
2. YouTube-transcript.io (free)
3. SocialKit (paid)
4. youtube-transcript-api (free, fallback)

**Example**:
```bash
# Transcribe 10 most recent episodes
dbb transcribe

# Transcribe 5 most recent episodes
dbb transcribe --recent 5

# Transcribe all episodes without transcripts (be careful with API limits)
dbb transcribe --recent 100

# Custom config
dbb transcribe --recent 20 --config ~/configs/testing.yaml
```

---

### `dbb summarize`
Generate summaries for episodes with transcripts but no summaries.

**Purpose**: Send transcripts to Ollama with channel-specific prompts. Uses local LLM (no cloud).

**Usage**:
```bash
dbb summarize --recent 10
dbb summarize --recent 5 --config config.yaml
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--recent` | INTEGER | `10` | Number of most recent episodes with transcripts but no summaries to process |
| `--config` | TEXT | `config.yaml` | Path to configuration file |

**Requirements**:
- Ollama must be running: `ollama serve`
- Model must be available: `ollama list`
- Configured in `config.yaml` and `.env`

**Channel-Specific Prompts**:
- Uses channel-specific prompts from `config.yaml` if configured
- Falls back to default prompt if channel not explicitly configured
- Prompts are Jinja2 templates with transcript context

**Example**:
```bash
# Summarize 10 most recent episodes (requires Ollama running)
ollama serve &
dbb summarize

# Summarize 5 specific episodes
dbb summarize --recent 5

# Summarize with custom config
dbb summarize --recent 20 --config ~/configs/production.yaml

# Check which episodes need summaries first
dbb status
```

---

### `dbb digest`
Generate weekly digest of episodes summarized in the past 7 days.

**Purpose**: Render beautiful HTML/text digests grouped by channel and optionally send via email.

**Usage**:
```bash
dbb digest
dbb digest --send
dbb digest --send --config config.yaml
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--send` | FLAG | `false` | Actually send emails; without flag, only previews are generated |
| `--config` | TEXT | `config.yaml` | Path to configuration file |

**Output Files** (when `--send` not used):
- `digest_preview.html` - HTML preview of digest
- `digest_preview.txt` - Plaintext preview of digest

**Email Configuration**:
- Uses `config.yaml` email settings
- If `send_separate_emails: true`: sends one email per channel to channel-specific recipients
- If `send_separate_emails: false`: sends combined digest to default recipients
- Uses channel-specific HTML/plaintext templates with CSS inlining

**Example**:
```bash
# Generate previews (no email sent)
dbb digest

# Preview digest
cat digest_preview.html

# Send emails to configured recipients
dbb digest --send

# Generate and send with custom config
dbb digest --send --config ~/configs/production.yaml

# Check status before sending
dbb status
dbb digest
# Review digest_preview.html
dbb digest --send
```

---

### `dbb status`
Show database statistics including per-channel breakdown.

**Purpose**: Display comprehensive statistics about episodes, transcripts, and summaries.

**Usage**:
```bash
dbb status
dbb status --config config.yaml
```

**Options**:
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config` | TEXT | `config.yaml` | Path to configuration file |

**Output**:
- **Overall Statistics**: Total episodes, transcripts, summaries with percentages
- **Per-Channel Breakdown**: Episodes, transcripts, summaries, and completion percentages for each channel
- **Completion Metrics**: Visual indicators of progress

**Example**:
```bash
# Show all statistics
dbb status

# With custom config
dbb status --config ~/configs/testing.yaml

# Monitor progress during bulk operations
dbb status
dbb transcribe --recent 20
dbb status  # Check progress
```

## Database Schema

### episodes table

```sql
CREATE TABLE episodes (
  -- Identity
  video_id            TEXT PRIMARY KEY,
  channel_id          TEXT,
  channel_title       TEXT,
  title               TEXT,
  url                 TEXT,
  published_at        TIMESTAMP,
  fetched_at          TIMESTAMP,

  -- Transcript
  transcript_md       TEXT,
  transcript_provider TEXT,
  transcript_language TEXT,
  transcript_checksum TEXT,
  transcript_length   INTEGER,
  transcript_path     TEXT,
  transcript_on_disk  BOOLEAN,

  -- Summary
  summary_md          TEXT,
  summary_model       TEXT,
  summary_created_at  TIMESTAMP,

  -- Metadata
  updated_at          TIMESTAMP
);
```

## Troubleshooting

### "YouTube API key not found"
- Ensure `.env` file exists and has `YOUTUBE_API_KEY` set
- Run `source .env` if using bash

### "Transcript providers failed"
- Check internet connection
- Verify API keys in `.env`
- Check provider status (they may be rate limited or down)
- Ensure `youtube-transcript-api` fallback is enabled

### "Ollama connection refused"
- Ensure Ollama is running: `ollama serve`
- Check `OLLAMA_HOST` in `.env` (default: http://localhost:11434)
- Verify model is downloaded: `ollama list`

### "SMTP authentication failed"
- Ensure Gmail app password is used (not regular password)
- Check `SMTP_USERNAME` and `SMTP_PASSWORD` in `.env`
- Enable 2FA on Gmail account first

### "Transcripts too short, trying next provider"
- Increase `min_chars` in `config.yaml` if false positives
- Or decrease if you want shorter transcripts accepted

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CLI (Click)                        │
├─────────────────────────────────────────────────────────┤
│  fetch → YouTube API → transcribe → Providers → DB      │
│  summarize → Ollama → DB                                │
│  digest → Render → Email (SMTP)                         │
├─────────────────────────────────────────────────────────┤
│              DuckDB (episodes table)                     │
├─────────────────────────────────────────────────────────┤
│          Local Storage (transcripts, summaries)          │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Idempotency** - Every command is safe to re-run
2. **DB as Source of Truth** - Full transcripts stored in DB (not just files)
3. **Multi-Provider Failover** - Automatic fallback if transcripts unavailable
4. **Privacy First** - Everything runs locally, no cloud LLMs
5. **Transparency** - Clear logging at every step

## Project Structure

```
duckdb-broadcast-briefs/
├── dbb/
│   ├── __init__.py
│   ├── cli.py              # Click CLI commands
│   ├── config.py           # Pydantic config
│   ├── db.py               # DuckDB operations
│   ├── youtube.py          # YouTube API client
│   ├── transcripts.py      # Transcript fetching
│   ├── summarize.py        # Ollama integration
│   ├── digest.py           # Email digest
│   └── utils.py            # Utilities
├── prompts/
│   └── summary_prompt.md   # Ollama prompt template
├── templates/
│   ├── digest.html         # Email HTML template
│   └── digest.txt          # Email text template
├── tests/
│   └── ...                 # Test suite
├── config.yaml.example
├── .env.example
├── pyproject.toml
├── README.md
└── AGENTS.md               # AI agent usage guide
```

## License

MIT License - see LICENSE file

---

**For detailed AI agent usage and advanced features, see [AGENTS.md](AGENTS.md)**
