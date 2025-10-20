Here’s the final requirements spec for DBB — DuckDB Broadcast Briefs (single-table model, API-only transcripts, DB-as-truth).

1) Purpose & Outcomes
	•	Stay current on long-form YouTube podcasts via a weekly email digest.
	•	Build a local, queryable archive (DuckDB) of all episodes with full transcripts and concise summaries for research/ideation.
	•	Private-first: summaries generated locally via Ollama.
	•	Idempotent: every command skips already-processed items.

⸻

2) High-Level Flow
	1.	Fetch (YouTube Data API)
	•	For each configured channel: resolve uploads playlist, paginate playlistItems (50/page), collect video_id, title, channel_id, channel_title, published_at, url.
	•	Insert new rows only; skip if video_id already exists.
	2.	Transcripts (API-only, with failover)
	•	Providers in order (configurable): Supadata → YouTube-transcript.io → SocialKit → youtube-transcript-api.
	•	Join all segments returned by a provider. If transcript length is suspiciously short (configurable threshold), try the next provider.
	•	On success:
a) Write local .md (reference only).
b) Read file bytes and store exact text in DB (transcript_md).
c) Save transcript_provider, transcript_language, transcript_checksum (SHA-256), transcript_length, transcript_path, transcript_on_disk=true.
	•	On failure across all providers: leave transcript fields NULL, log “unavailable”.
	•	No Whisper, no audio downloads.
	3.	Summaries (local via Ollama)
	•	Worklist = episodes where transcript_md IS NOT NULL and summary_md IS NULL.
	•	Read transcript from DuckDB (DB is canonical; do not read files).
	•	Generate Markdown summary with prompts/summary_prompt.md; save to summary_md, summary_model, summary_created_at.
	4.	Weekly Digest (email + preview)
	•	Query episodes with summary_created_at in the last 7 days.
	•	Render HTML + plaintext (Jinja2 templates, Premailer CSS inlining), grouped by channel, with a TOC.
	•	Always write digest_preview.html/.txt; if email.enabled=true, send via SMTP.
	5.	Housekeeping
	•	purge-transcripts: only delete local .md files when their file SHA-256 equals transcript_checksum; then set transcript_on_disk=false. DB retains full transcripts.

⸻

3) Single-Table Schema (source of truth)

Table: episodes

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
  transcript_md       TEXT,        -- full transcript markdown (NULL until fetched)
  transcript_provider TEXT,        -- 'supadata' | 'ytio' | 'socialkit' | 'youtube_transcript_api'
  transcript_language TEXT,        -- e.g., 'en'
  transcript_checksum TEXT,        -- sha256(content)
  transcript_length   INTEGER,     -- LEN(transcript_md)
  transcript_path     TEXT,        -- local reference .md (may be deleted)
  transcript_on_disk  BOOLEAN,     -- does path currently exist?

  -- Summary (local via Ollama)
  summary_md          TEXT,        -- markdown summary (NULL until created)
  summary_model       TEXT,        -- e.g., 'llama3.1:8b'
  summary_created_at  TIMESTAMP,

  -- Bookkeeping
  updated_at          TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_episodes_channel_date
  ON episodes (channel_title, COALESCE(published_at, fetched_at) DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_summary_created
  ON episodes (summary_created_at DESC);


⸻

4) CLI Commands & Idempotency Rules

yt init-db
	•	Create episodes table and indexes.
	•	Ensure data/transcripts, data/summaries directories exist.

yt fetch [--config]
	•	Use YouTube Data API; page uploads playlist for each channel.
	•	Insert only new episodes (skip if video_id exists).
	•	Store: identity + catalog columns; set fetched_at=NOW(), updated_at=NOW().

yt transcribe --recent N [--config]
	•	Select N most recent episodes where transcript_md IS NULL.
	•	Attempt providers in configured order; join all segments; guard with min length (e.g., 400 chars; configurable).
	•	On success: write local .md → read back → update transcript columns + updated_at.
	•	On failure: leave transcript columns NULL (visible in analytics), log a warning.

yt summarize --recent N [--private] [--config]
	•	Select N most recent episodes where transcript_md IS NOT NULL AND summary_md IS NULL.
	•	Read transcript from DB; generate summary via Ollama (local host/model from config/env).
	•	Update summary columns + updated_at.

yt digest --week [--send] [--intro "..."] [--config]
	•	Window: last 7 days by summary_created_at.
	•	Render HTML + TXT with templates; write previews; if enabled, send email via SMTP.

yt purge-transcripts [--dry-run True|False] [--config]
	•	For rows with transcript_on_disk=true and a valid transcript_path:
	•	Compute file SHA-256; compare to transcript_checksum.
	•	On match: delete file, set transcript_on_disk=false, bump updated_at.
	•	On mismatch: do not delete; log error.

⸻

5) Config (single file)

db_path: ./dbb.duckdb
data_dir: ./data
transcript_dir: ./data/transcripts
summary_dir: ./data/summaries

channels:
  - name: "Lex Fridman"
    channel_id: "UCSHZKyawb77ixDdsGog4iWA"
  - name: "Darius Daniels Podcast"
    channel_id: "<ID>"

fetch:
  use_youtube_api: true
  api_key_env: "YOUTUBE_API_KEY"
  max_per_channel: null

transcripts_providers:
  order: ["supadata", "ytio", "socialkit", "youtube_transcript_api"]
  min_chars: 400          # sanity check threshold
  supadata:  { base_url: "https://api.supadata.ai/v1/youtube/transcript", api_key: "${SUPADATA_API_KEY}", timeout_s: 30 }
  ytio:      { base_url: "https://www.youtube-transcript.io/api", timeout_s: 30 }
  socialkit: { base_url: "https://api.socialkit.dev/youtube-transcript", api_key: "${SOCIALKIT_API_KEY}", timeout_s: 30 }
  youtube_transcript_api: { enabled: true, languages: ["en"], timeout_s: 30 }

summarize:
  ollama_host: "http://localhost:11434"
  ollama_model: "llama3.1:8b"
  prompt_path: "./prompts/summary_prompt.md"

email:
  enabled: true
  from_name: "DBB Weekly"
  from_email: "your_email@gmail.com"
  recipients: ["you@example.com"]
  subject_format: "Your Weekly Podcast Digest ({{ start_date }} – {{ end_date }})"

Env vars (.env.example)
YOUTUBE_API_KEY, SUPADATA_API_KEY, SOCIALKIT_API_KEY, SMTP_HOST, SMTP_PORT, SMTP_USE_TLS, SMTP_USERNAME, SMTP_PASSWORD, OLLAMA_HOST, OLLAMA_MODEL.

⸻

6) Providers — Implementation Notes
	•	Each adapter returns full joined text.
	•	If returned text < min_chars → treat as partial and try next provider.
	•	Language: set from provider if available; otherwise default "en" (configurable later with autodetect).
	•	On success, compute transcript_checksum = sha256(transcript_md) and transcript_length = len(transcript_md).

⸻

7) Email Digest — Rendering Requirements
	•	HTML (Jinja2 + Premailer CSS inline), plus Plaintext fallback.
	•	Group by channel_title, ordered by COALESCE(published_at, fetched_at) DESC.
	•	Include TOC with anchors, Watch link, and (if present) Transcript link to local path.
	•	Always write digest_preview.html / digest_preview.txt to repo root.

⸻

8) Non-Goals / Explicit Omissions
	•	No Whisper or audio downloading (no audio_dir).
	•	No cloud LLMs by default (Ollama only; can be added later).
	•	No second/third tables (everything lives in episodes).

⸻

9) Acceptance Criteria
	•	yt init-db creates episodes and indexes successfully.
	•	yt fetch inserts only new episodes; re-runs do not duplicate and are cheap.
	•	yt transcribe fills transcript columns only for episodes where transcript_md IS NULL; retries providers as needed; stores full text, checksum, language; writes local .md and confirms DB save.
	•	yt summarize creates summaries only for episodes where summary_md IS NULL and transcript exists; uses DB transcript.
	•	yt digest --week renders previews and, when enabled, sends email.
	•	yt purge-transcripts deletes only checksum-matching files and updates flags accordingly.

⸻

10) Nice-to-haves (future)
	•	Add duration_seconds (via videos.list) and surface in digest cards.
	•	Add status virtuals for analytics views (e.g., “missing transcripts”).
	•	Add embeddings (duckdb + pgvecto.rs/extension) for semantic search.
	•	Add yt diagnose --video <id> to print per-provider results and lengths.

⸻

If you want this compiled into a README.md + AGENT.md pair (ready to paste into your repo), say the word and I’ll generate them exactly to spec.