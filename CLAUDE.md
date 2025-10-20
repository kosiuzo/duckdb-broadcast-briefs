# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DuckDB Broadcast Briefs** is a privacy-first YouTube podcast archiving tool that:
- Fetches episodes from YouTube channels via API
- Transcribes episodes using multiple fallback providers (Supadata → YouTube-transcript.io → SocialKit → youtube-transcript-api)
- Generates summaries locally using Ollama (no cloud LLMs)
- Sends beautiful HTML weekly digest emails via SMTP
- Stores everything in a queryable DuckDB database

**Key Design Principles**: Idempotency (all operations are safe to re-run), multi-provider failover, local-first privacy, database as source of truth.

## Repository Structure

```
duckdb-broadcast-briefs/
├── dbb/                        # Main package
│   ├── cli.py                  # Click CLI commands (init-db, fetch, transcribe, summarize, digest, purge, status)
│   ├── config.py               # Pydantic config management (loads from config.yaml + .env)
│   ├── db.py                   # DuckDB operations and schema
│   ├── youtube.py              # YouTube Data API client
│   ├── transcripts.py          # Multi-provider transcript fetching with failover
│   ├── summarize.py            # Ollama integration for summarization
│   ├── digest.py               # HTML digest rendering and SMTP sending
│   └── utils.py                # Shared utilities (checksums, file ops, etc)
├── prompts/
│   └── summary_prompt.md       # Jinja2 template for Ollama summarization
├── tests/
│   ├── conftest.py             # Pytest fixtures (temp db, config)
│   ├── test_config.py          # Config loading and validation
│   ├── test_db.py              # Database operations
│   └── test_utils.py           # Utility functions
├── docs/                       # Documentation (setup, requirements, implementation plans)
├── config.yaml.example         # Example channel configuration
├── .env.example                # Example environment variables
├── pyproject.toml              # Project metadata, dependencies, tool configs
└── README.md                   # User-facing documentation
```

## Development Setup

### Prerequisites
- Python 3.9+
- Virtual environment (strongly recommended)
- Git

### Initial Setup
```bash
# Clone and navigate
git clone <repo> && cd duckdb-broadcast-briefs

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy configuration templates
cp config.yaml.example config.yaml
cp .env.example .env

# Edit config.yaml with your YouTube channels and .env with API keys
```

### Required API Keys & Services
- **YouTube Data API**: Get from Google Cloud Console (`YOUTUBE_API_KEY`)
- **Transcript Provider** (at least one):
  - Supadata (paid, reliable) - set `SUPADATA_API_KEY`
  - YouTube-transcript.io (free) - no key needed
  - SocialKit (paid) - set `SOCIALKIT_API_KEY`
- **Ollama** (for summarization): Run locally on `http://localhost:11434`
- **Gmail SMTP** (for digests): Generate app password, set `SMTP_USERNAME` and `SMTP_PASSWORD`

## Common Commands

### Development
```bash
# Run tests with coverage
pytest

# Run single test file
pytest tests/test_db.py

# Run single test function
pytest tests/test_db.py::test_insert_episode

# Format code (100 char line length)
black dbb tests

# Lint code
ruff check dbb tests

# Type checking
mypy dbb --ignore-missing-imports

# Initialize database (must run before first fetch)
dbb initdb
```

### CLI Operations
```bash
# Always activate venv first: source venv/bin/activate

# Fetch latest episodes from all configured channels
dbb fetch

# Get transcripts for 10 most recent episodes without them
dbb transcribe --recent 10

# Generate summaries (requires Ollama running)
dbb summarize --recent 10

# Generate and send weekly digest
dbb digest --send

# Preview digest without sending
dbb digest

# Show database statistics
dbb status

# Delete transcript files (with safety checks)
dbb purge --dry-run
```

## Architecture & Code Flow

### Main Flow
1. **CLI Entry** (`cli.py`) → Parse commands and options
2. **Config Loading** (`config.py`) → Load YAML + environment variables via Pydantic
3. **Database** (`db.py`) → Connect to DuckDB, manage schema and transactions
4. **YouTube Fetching** (`youtube.py`) → Call YouTube Data API, format episode data
5. **Transcription** (`transcripts.py`) → Try providers in order (supadata → ytio → socialkit → fallback)
6. **Summarization** (`summarize.py`) → Send transcript to Ollama with prompt template
7. **Digest** (`digest.py`) → Render HTML template, send via SMTP

### Key Classes & Responsibilities

**DatabaseManager** (`db.py`)
- Manages DuckDB connection lifecycle
- Initializes schema (episodes table with indexed fields)
- CRUD operations: `insert_episode()`, `get_episode()`, `update_episode()`
- Database statistics and queries

**Config & Subconfigs** (`config.py`)
- **ChannelConfig**: YouTube channel name + ID
- **FetchConfig**: YouTube API settings
- **TranscriptProviderConfig**: API endpoints and credentials for each provider
- **SummarizeConfig**: Ollama host, model, timeout
- **EmailConfig/SmtpConfig**: Email digest settings
- **Config** (main): Loads from `config.yaml` + env vars via `load_config()`

**YouTubeClient** (`youtube.py`)
- `fetch_channel_episodes()`: Query YouTube API for channel uploads playlist
- Returns list of Episode dicts with video_id, title, channel_title, published_at, url

**TranscriptManager** (`transcripts.py`)
- `fetch_transcript()`: Try providers in configured order
- Multi-provider failover with timeout and minimum length validation
- Falls back to youtube-transcript-api as last resort

**SummarizerManager** (`summarize.py`)
- `summarize_transcript()`: POST transcript to Ollama with Jinja2-rendered prompt
- Handles timeouts and retries
- Returns summary text

**DigestRenderer/DigestSender** (`digest.py`)
- `render_digest()`: Query recent summaries, format HTML/text via Jinja2 templates
- `send_digest()`: SMTP connection, CSS inlining via premailer
- `save_digest_previews()`: Save HTML/text to disk for preview

### Database Schema
**episodes table** (video_id = PRIMARY KEY)
- Identity: video_id, channel_id, channel_title, title, url, published_at, fetched_at
- Transcript: transcript_md, transcript_provider, transcript_language, transcript_checksum, transcript_length, transcript_path, transcript_on_disk
- Summary: summary_md, summary_model, summary_created_at
- Metadata: updated_at

## Testing

### Test Fixtures
- **tmp_db_config** (conftest.py): Creates temp DuckDB for tests
- **sample_episodes**: Pre-defined test episode data

### Running Tests
```bash
pytest                          # All tests
pytest tests/test_db.py -v      # Verbose output
pytest -k "test_insert"         # Run tests matching keyword
pytest --cov=dbb               # With coverage report
```

### Test Organization
- `test_config.py`: Config loading, env var resolution, validation
- `test_db.py`: Database operations (insert, update, query)
- `test_utils.py`: Utility functions (checksums, file operations)
- No unit tests for external APIs (YouTube, Ollama, SMTP) - mocked in integration tests

## Code Style & Standards

### Formatting & Linting
- **Line Length**: 100 characters (enforced by black)
- **Formatter**: Black
- **Linter**: Ruff (E, F, W rules, ignores E501)
- **Type Checking**: MyPy (optional defs allowed, missing imports ignored)

### Configuration in pyproject.toml
```toml
[tool.black]
line-length = 100
target-version = ["py310", "py311", "py312"]

[tool.ruff]
line-length = 100
select = ["E", "F", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=dbb --cov-report=term-missing"
```

### Code Patterns
- **Error Handling**: Try-except with logging, user-friendly error messages via console
- **Context Managers**: Use `with` for database and file operations
- **Idempotency**: All operations check for existing data before inserting/updating
- **Logging**: Use `logger = logging.getLogger(__name__)` in all modules
- **Rich Output**: Use `Console` from rich for formatted CLI output

## Configuration Files

### config.yaml
Specifies:
- `channels`: List of {name, channel_id} to monitor
- `fetch`: max_per_channel, api_key_env
- `transcripts`: Provider order, timeouts, individual provider configs
- `summarize`: Ollama host, model, prompt path, timeouts
- `email`: enabled, from_name, from_email, recipients, subject template
- `smtp`: host, port, use_tls, username/password env vars
- `db_path`: Where DuckDB file lives (default: "./dbb.duckdb")
- `log_level`: Logging verbosity

### .env
Contains sensitive values:
- `YOUTUBE_API_KEY`
- `SUPADATA_API_KEY` (optional)
- `SOCIALKIT_API_KEY` (optional)
- `OLLAMA_HOST` (optional, default: http://localhost:11434)
- `SMTP_USERNAME`, `SMTP_PASSWORD`

## Common Development Tasks

### Adding a New CLI Command
1. Add command function in `cli.py` with `@main.command()` decorator
2. Define options with `@click.option()`
3. Follow existing pattern: load config → initialize managers → execute → cleanup
4. Use `console.print()` for output and logging

### Adding a New Transcript Provider
1. Add provider config to `TranscriptsConfig` in `config.py`
2. Add fetch logic in `TranscriptManager._fetch_provider_*()` in `transcripts.py`
3. Add to `order` list in config for failover chain
4. Document in README

### Debugging Failed Transcription
- Check `OLLAMA_HOST` and verify Ollama is running: `curl http://localhost:11434/api/tags`
- Check provider order in config.yaml - free providers (ytio) may hit rate limits
- Enable debug logging in config.yaml (`log_level: DEBUG`)
- Check API keys in .env for paid providers

### Database Inspection
```bash
# Query DuckDB directly
duckdb dbb.duckdb

# In DuckDB shell:
SELECT COUNT(*) FROM episodes;
SELECT * FROM episodes WHERE channel_title = 'Lex Fridman' LIMIT 5;
SELECT video_id, title, summary_created_at FROM episodes WHERE summary_md IS NOT NULL ORDER BY summary_created_at DESC LIMIT 10;
```

## Key Dependencies

**Core Libraries**:
- `duckdb`: Embedded SQL database
- `click`: CLI framework
- `pydantic`: Config validation
- `pyyaml`: YAML parsing

**External APIs**:
- `google-api-python-client`: YouTube Data API
- `youtube-transcript-api`: Fallback transcript provider
- `httpx`: HTTP client for transcript providers
- `requests`: General HTTP

**Output & UI**:
- `rich`: Formatted console output
- `jinja2`: Template rendering (prompts, digest HTML)
- `premailer`: CSS inlining for email

**Dev Tools**:
- `pytest`, `pytest-cov`: Testing
- `black`: Code formatting
- `ruff`: Linting
- `mypy`: Type checking

## Important Notes

1. **Virtual Environment Required**: Always activate venv before running CLI commands
2. **Idempotency**: Safe to re-run all commands - database checks prevent duplicates
3. **Local Privacy**: No cloud LLMs - all summarization via local Ollama
4. **Multi-Provider Failover**: Transcript fetching automatically tries providers in order
5. **Database is Source of Truth**: Full transcripts stored in DB, not just files on disk
6. **Configuration Precedence**: Env vars override config.yaml values
7. **Logging**: Set `log_level: DEBUG` in config.yaml for troubleshooting

## When Making Changes

- Run full test suite: `pytest --cov=dbb`
- Format code: `black dbb tests`
- Check types: `mypy dbb --ignore-missing-imports`
- Test CLI manually: `dbb status`, `dbb fetch`, etc.
- Update tests for new functionality
- Maintain idempotency in all operations
