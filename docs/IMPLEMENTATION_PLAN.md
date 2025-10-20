# DuckDB Broadcast Briefs — Implementation Plan

## Overview
Building a YouTube podcast archive system with local transcription via APIs and local summarization via Ollama. Single-table DuckDB schema, CLI-driven, idempotent operations.

**Key Principles:**
- Idempotency First — Every command is re-runnable without side effects
- DB as Source of Truth — Transcripts stored in `transcript_md` column (never read files)
- API Resilience — Multi-provider failover with timeout + retry logic
- Separation of Concerns — Single responsibility modules

---

## Phase 1: Foundation — Project Structure & Config
- [ ] Create project structure (`dbb/`, `tests/`, `prompts/`, `templates/`, `data/`)
- [ ] Build Pydantic config schema with environment variable interpolation
- [ ] Create `config.yaml.example` template
- [ ] Implement config loader with validation
- [ ] Set up logging configuration
- [ ] Create `.env.example` with all required API keys

**Dependencies to add:**
- duckdb, pydantic, click, pyyaml, python-dotenv, requests, jinja2, premailer, google-api-python-client

---

## Phase 2: Database — DuckDB Schema & Init Command

### 2.1 Database Schema
- [ ] Design and implement DuckDB schema (episodes table + indexes)
  - Table: `episodes` with all identity, transcript, summary, and bookkeeping columns
  - Index: `idx_episodes_channel_date` (channel_title, published_at DESC)
  - Index: `idx_episodes_summary_created` (summary_created_at DESC)

### 2.2 Init Command
- [ ] Implement `dbb/db.py` with database connection management
- [ ] Implement schema creation functions
- [ ] Implement directory creation (data/transcripts, data/summaries)
- [ ] Implement `yt init-db` CLI command
- [ ] Test: Run init-db, verify schema created with correct columns/indexes

---

## Phase 3: YouTube Fetch — API Integration

### 3.1 YouTube API Client
- [ ] Implement `dbb/youtube.py` with YouTube Data API client
  - Resolve uploads playlist for each channel
  - Paginate playlistItems (50/page)
  - Collect video_id, title, channel_id, channel_title, published_at, url
  - Handle API errors and quota exhaustion gracefully

### 3.2 Fetch Command
- [ ] Implement `yt fetch` command
  - Load config and validate YouTube API key
  - For each configured channel, fetch all new videos
  - Insert only new episodes (skip if video_id exists) — idempotent
  - Set fetched_at=NOW(), updated_at=NOW()
  - Log progress and results
- [ ] Test: Run fetch, verify episodes inserted; run again, verify no duplicates

---

## Phase 4: Transcripts — Multi-Provider Failover

### 4.1 Transcript Provider Architecture
- [ ] Implement abstract `TranscriptProvider` base class in `dbb/transcripts.py`
- [ ] Implement provider adapters:
  - [ ] Supadata adapter (API key, timeout)
  - [ ] YouTube-transcript.io adapter (free tier)
  - [ ] SocialKit adapter (API key, timeout)
  - [ ] youtube-transcript-api adapter (fallback Python library)
- [ ] Each adapter: `fetch(video_id) → (transcript_text, language) or raise TranscriptUnavailable`

### 4.2 Transcript Orchestration
- [ ] Implement transcript orchestration logic with:
  - Provider chaining in configured order
  - Sanity check: reject if `len(transcript) < min_chars` (configurable)
  - SHA-256 hash generation (`transcript_checksum`)
  - Length calculation (`transcript_length`)
  - Language detection/default to "en"

### 4.3 Transcribe Command
- [ ] Implement `yt transcribe --recent N` command
  - Select N most recent episodes WHERE transcript_md IS NULL
  - Attempt providers in order
  - On success: write local `.md` file → read back → update transcript columns + updated_at
  - On failure across all providers: leave transcript_md NULL, log warning
  - Set transcript_on_disk=true after successful write
- [ ] Test: Run transcribe, verify transcript columns populated; verify .md files created

---

## Phase 5: Summarization — Ollama Integration

### 5.1 Ollama Integration
- [ ] Create `prompts/summary_prompt.md` template for Ollama
  - Template should request: Overview, Key Points, Speakers, Resources/Takeaways
- [ ] Implement Ollama client in `dbb/summarize.py`
  - HTTP calls to ollama_host (configurable, default localhost:11434)
  - Timeout + retry logic with exponential backoff
  - Connection error handling

### 5.2 Summarize Command
- [ ] Implement `yt summarize --recent N` command
  - Select N most recent episodes WHERE transcript_md IS NOT NULL AND summary_md IS NULL
  - Read transcript_md from DB (not from files)
  - Generate summary via Ollama with prompt template
  - Update: summary_md, summary_model, summary_created_at, updated_at
  - Handle Ollama failures gracefully (skip episode, log warning, continue)
- [ ] Test: Run summarize, verify summary columns populated

---

## Phase 6: Email Digest — Templates & Rendering

### 6.1 Email Templates
- [ ] Create `templates/digest.html` (Jinja2 template)
  - Include TOC with anchors
  - Group by channel_title
  - For each episode: title, published_at, summary snippet, watch link, transcript link
  - Apply Premailer for CSS inlining
- [ ] Create `templates/digest.txt` (plaintext fallback)
  - Same content structure without HTML

### 6.2 Digest Rendering & Sending
- [ ] Implement digest renderer in `dbb/digest.py`
  - Query episodes WHERE summary_created_at >= NOW() - 7 days
  - Render HTML + plaintext from templates
  - Apply Premailer for CSS inlining
  - Generate subject line from template (with start_date/end_date)

### 6.3 SMTP Email Sending
- [ ] Implement SMTP email client
  - Load credentials from config (from_email, recipients, SMTP_HOST/PORT/USERNAME/PASSWORD)
  - Send multipart email (HTML + plaintext)
  - Handle send failures gracefully (log error, but don't fail command)

### 6.4 Digest Command
- [ ] Implement `yt digest --week [--send] [--intro "..."]` command
  - Render HTML + TXT previews
  - Always write `digest_preview.html` and `digest_preview.txt` to repo root
  - If `--send` flag and email.enabled=true, send via SMTP
  - Include optional `--intro` text in digest body
- [ ] Test: Run digest, verify preview files created; test email sending if enabled

---

## Phase 7: Housekeeping — Purge Transcripts

### 7.1 Purge Command
- [ ] Implement `yt purge-transcripts [--dry-run True|False]` command
  - For each row with transcript_on_disk=true and valid transcript_path:
    - Compute file SHA-256
    - Compare to transcript_checksum
    - If match: delete file, set transcript_on_disk=false, bump updated_at
    - If mismatch: log error, do not delete
  - Respect `--dry-run` flag (preview changes without executing)
  - DB retains full transcripts (only deletes files)
- [ ] Test: Create transcript files, run purge, verify files deleted and DB flags updated

---

## Phase 8: CLI & Polish

### 8.1 CLI Infrastructure
- [ ] Wire all commands into Click CLI framework
- [ ] Add `--config` flag to all commands (optional, defaults to config.yaml)
- [ ] Add proper help text and docstrings for all commands
- [ ] Implement config validation at CLI entry

### 8.2 Logging & Error Handling
- [ ] Implement comprehensive logging throughout:
  - DEBUG: API calls, internal operations
  - INFO: Command progress, successful operations
  - WARNING: API failures, skipped items, recoverable errors
  - ERROR: Fatal errors, failed commands
- [ ] Create helpful error messages for common failures
- [ ] Add progress indicators for long operations (rich library optional)

### 8.3 CLI Testing
- [ ] Test each command with various argument combinations
- [ ] Test config loading and validation
- [ ] Test error handling (missing API keys, invalid paths, etc.)

---

## Phase 9: Testing — Unit & Integration Tests

### 9.1 Unit Tests
- [ ] Test config validation (Pydantic schema)
- [ ] Test hash generation (SHA-256)
- [ ] Test URL/path construction
- [ ] Test CLI argument parsing
- [ ] Test individual transcript provider adapters (mock HTTP responses)

### 9.2 Integration Tests
- [ ] Create temp DuckDB for testing
- [ ] Test `init-db` → schema created correctly
- [ ] Test `fetch` → episodes inserted (mock YouTube API)
- [ ] Test `transcribe` → transcript columns populated (mock transcript APIs)
- [ ] Test `summarize` → summary columns populated (mock Ollama)
- [ ] Test `digest` → preview files generated
- [ ] Test idempotency: run same command twice, verify no duplicates/side effects

### 9.3 Test Fixtures
- [ ] Create fixtures for YouTube API responses
- [ ] Create fixtures for transcript API responses (Supadata, YT-IO, SocialKit, youtube-transcript-api)
- [ ] Create fixtures for Ollama responses
- [ ] Create sample episode data for testing

### 9.4 Coverage & Quality
- [ ] Achieve >80% test coverage
- [ ] Run linting (flake8 or ruff)
- [ ] Run type checking (mypy)

---

## Phase 10: Documentation & Deployment

### 10.1 Requirements & Setup
- [ ] Create `requirements.txt` with all dependencies pinned
- [ ] Create `setup.py` or `pyproject.toml` with package metadata
- [ ] Create `.env.example` with all required environment variables
- [ ] Create `config.yaml.example` with all configuration options

### 10.2 Documentation
- [ ] Write comprehensive `README.md`:
  - Project overview and purpose
  - Quick start (installation, setup, first run)
  - Configuration guide (config.yaml, environment variables)
  - CLI command reference (yt init-db, fetch, transcribe, summarize, digest, purge-transcripts)
  - Architecture overview
  - Troubleshooting guide
  - Contributing guidelines
- [ ] Add docstrings to all modules and functions
- [ ] Document API requirements (YouTube Data API, transcript providers, Ollama)

### 10.3 Quality Gates
- [ ] Run full test suite and verify all tests pass
- [ ] Run linting and fix any issues
- [ ] Run type checking and fix any issues
- [ ] Verify all CLI commands work end-to-end
- [ ] Test with real YouTube channels (if possible)

---

## Summary of Key Files to Create

### Source Code
- `dbb/__init__.py`
- `dbb/cli.py` — Click CLI entry point
- `dbb/config.py` — Pydantic config schema
- `dbb/db.py` — DuckDB operations
- `dbb/youtube.py` — YouTube API client
- `dbb/transcripts.py` — Multi-provider transcript fetching
- `dbb/summarize.py` — Ollama integration
- `dbb/digest.py` — Email digest rendering
- `dbb/utils.py` — Helpers (hashing, logging, file ops)

### Templates & Prompts
- `templates/digest.html` — Email HTML template
- `templates/digest.txt` — Email plaintext template
- `prompts/summary_prompt.md` — Ollama summary prompt

### Configuration & Docs
- `config.yaml.example` — Configuration template
- `.env.example` — Environment variables template
- `requirements.txt` — Python dependencies
- `README.md` — Comprehensive documentation
- `IMPLEMENTATION_PLAN.md` — This file

### Tests
- `tests/__init__.py`
- `tests/test_config.py`
- `tests/test_db.py`
- `tests/test_youtube.py`
- `tests/test_transcripts.py`
- `tests/test_summarize.py`
- `tests/test_digest.py`
- `tests/test_cli.py`
- `tests/conftest.py` — Fixtures

---

## Progress Tracking

**Status:** Planning phase complete ✓
**Next:** Phase 1 — Foundation (project structure, config, dependencies)

Update this file as tasks are completed.
