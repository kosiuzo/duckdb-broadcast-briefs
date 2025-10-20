# Channel-Specific Email Digests

This document explains how to configure and use the channel-specific email digest feature.

## Overview

The email digest system now supports sending separate, customized emails for each podcast channel. Each channel receives:

- A personalized email with only their episodes
- Customized digest using their specific summarization prompt
- Channel-specific recipients (optional)
- Professional channel-focused styling

## Key Features

✅ **Separate Emails Per Channel**
- Each podcast gets its own email digest
- Recipients receive only the content they're interested in
- No mixing of different podcast content

✅ **Customized Email Templates**
- Professional HTML and plaintext templates
- Episode count per channel
- Clear channel branding in subject line

✅ **Channel-Specific Recipients**
- Configure different recipients for each channel
- Fallback to default recipients if not configured
- Easy to add multiple recipients per channel

✅ **Smart Fallback**
- Combined digest option still available
- Falls back to default recipients if channel not configured
- Graceful handling of missing configurations

✅ **Integrated with Prompts**
- Uses the same channel-specific summarization prompts
- Consistent formatting between summaries and emails

## Configuration

### Basic Setup

In `config.yaml`, configure the email section:

```yaml
email:
  enabled: true
  from_name: "DBB Weekly"
  from_email: "${SMTP_USERNAME}"
  recipients:
    - "default@example.com"  # Fallback recipients
  subject_format: "Your Weekly Podcast Digest ({{ start_date }} – {{ end_date }})"

  # IMPORTANT: Enable separate emails per channel
  send_separate_emails: true

  # Channel-specific recipients
  channel_recipients:
    "How I AI":
      - "user1@example.com"
    "The AI Daily Brief: Artificial Intelligence News Podcast":
      - "user2@example.com"
      - "user3@example.com"  # Multiple recipients per channel
```

### Configuration Options

#### `send_separate_emails` (boolean)

**Default**: `true`

Controls whether to send separate emails for each channel or a combined digest.

- **`true`**: Sends one email per channel (recommended)
  - Each email contains only that channel's episodes
  - Uses channel-specific recipient list
  - Subject line includes channel name
  - Much clearer for subscribers

- **`false`**: Sends a single combined digest
  - Original behavior: all channels in one email
  - Uses default recipients
  - Subject line is generic
  - Table of contents with channel links

#### `recipients` (list of emails)

**Default**: `[]`

Default email recipients used as:
1. Fallback if channel-specific recipients not configured
2. All recipients if `send_separate_emails: false`
3. Automatic recipients for channels without explicit configuration

#### `channel_recipients` (dictionary)

**Default**: `{}`

Maps channel names to their specific recipient lists.

```yaml
channel_recipients:
  "Channel Name": ["email1@example.com", "email2@example.com"]
```

**Important**: Channel name must match `channel_title` in database exactly (case-sensitive).

## How It Works

### Separate Email Mode (Recommended)

When `send_separate_emails: true`:

```
Command: dbb digest --send

↓

1. Fetch recent episodes (past 7 days)
2. Group by channel
3. For each channel:
   a. Render channel-specific digest (using channel's prompt)
   b. Convert to HTML and plaintext
   c. Inline CSS for email compatibility
   d. Send to channel-specific recipients

↓

Result: One professional email per channel
```

### Example Email Flow

**Channel: "How I AI"**
- Recipient: user@example.com
- Subject: "How I AI Weekly Digest (2024-10-13 – 2024-10-20)"
- Content: Only How I AI episodes with AI-focused summaries

**Channel: "The AI Daily Brief"**
- Recipients: user2@example.com, user3@example.com
- Subject: "The AI Daily Brief Weekly Digest (2024-10-13 – 2024-10-20)"
- Content: Only AI Daily Brief episodes with news-focused summaries

## Email Templates

Two templates are used for channel-specific digests:

### `templates/channel_digest.html`

Professional HTML email template with:
- Channel name as header
- Week date range
- Episode count badge
- Individual episode cards
- YouTube and transcript links
- Professional styling

**Variables Available**:
- `channel_name` - Name of the channel
- `start_date` - Week start date (YYYY-MM-DD)
- `end_date` - Week end date (YYYY-MM-DD)
- `episode_count` - Number of episodes
- `episodes` - List of episode objects

### `templates/channel_digest.txt`

Plaintext email template with:
- Clean text formatting
- Episode numbers
- Publication dates
- Full episode summaries
- Links to YouTube and transcripts

## CLI Commands

### Generate and Preview Digests

```bash
dbb digest
```

- Generates digests for all channels
- Saves HTML and plaintext previews
- Does NOT send emails (unless `--send` is used)

### Generate and Send Emails

```bash
dbb digest --send
```

- Generates digests for all channels
- Sends separate email for each channel (if `send_separate_emails: true`)
- Respects channel-specific recipient configuration
- Reports success/failure for each channel

### Send Combined Digest (Legacy)

To send a single combined email with all channels:

1. Set `send_separate_emails: false` in config.yaml
2. Run: `dbb digest --send`

## Setup Guide

### Step 1: Identify Channels

List all channels in your database:

```bash
duckdb dbb.duckdb
SELECT DISTINCT channel_title FROM episodes;
```

Note the exact channel names (case-sensitive).

### Step 2: Configure Recipients

In `config.yaml`, add each channel with its recipients:

```yaml
channel_recipients:
  "How I AI":
    - "alice@example.com"
  "The AI Daily Brief: Artificial Intelligence News Podcast":
    - "bob@example.com"
    - "charlie@example.com"
```

### Step 3: Set Default Recipients

Add a default fallback for any channels not explicitly configured:

```yaml
recipients:
  - "default@example.com"
```

### Step 4: Enable Separate Emails

```yaml
send_separate_emails: true
```

### Step 5: Test

```bash
# Generate preview digests
dbb digest

# Check HTML preview
cat digest_preview.html

# Send test emails
dbb digest --send
```

## Advanced Configuration

### Different Recipients per Channel

```yaml
channel_recipients:
  "How I AI":
    - "dev-team@example.com"
    - "ai-fans@example.com"
  "The AI Daily Brief: Artificial Intelligence News Podcast":
    - "news-team@example.com"
  "Another Podcast":
    - "general@example.com"
    - "podcast-admins@example.com"
```

### Fallback to Default

If a channel is not in `channel_recipients`, uses default recipients:

```yaml
recipients:
  - "everyone@example.com"

channel_recipients:
  "Popular Channel":
    - "special-recipients@example.com"
  # "Other Channel" not listed → uses default recipients
```

### Combined Mode

To send one email with all channels:

```yaml
send_separate_emails: false
recipients:
  - "all-recipients@example.com"
```

## Email Format Comparison

### Separate Emails (Recommended)

✅ Cleaner, focused content
✅ Each channel gets spotlight
✅ Recipients only see relevant episodes
✅ Professional appearance
✅ No navigation needed

**Subject**: "How I AI Weekly Digest (2024-10-13 – 2024-10-20)"
**Content**: Only How I AI episodes

### Combined Digest

⚠️ All channels in one email
⚠️ Table of contents for navigation
⚠️ Recipients see all content
⚠️ Works for small podcast lists

**Subject**: "Your Weekly Podcast Digest (2024-10-13 – 2024-10-20)"
**Content**: All channels grouped with headers

## Troubleshooting

### Recipients Not Receiving Emails

**Issue**: Email is not reaching recipients

**Solution**:
1. Check email is enabled: `email.enabled: true`
2. Verify channel name in `channel_recipients` matches database exactly
   ```bash
   SELECT DISTINCT channel_title FROM episodes;
   ```
3. Check SMTP configuration: `smtp.host`, `smtp.port`, credentials
4. Check logs: Set `logging.level: DEBUG` and look for SMTP errors

### Channel Name Mismatch

**Issue**: Using default recipients instead of channel-specific ones

**Solution**:
1. Get exact channel name:
   ```bash
   duckdb dbb.duckdb
   SELECT DISTINCT channel_title FROM episodes WHERE channel_title LIKE '%Channel%';
   ```
2. Copy exact spelling and case
3. Update config.yaml with exact match
4. Restart application (if running as daemon)

### Email Content Issues

**Issue**: Email formatting looks wrong or summaries missing

**Solution**:
1. Check digest previews: `cat digest_preview.html`
2. Verify channel-specific prompts are configured
3. Confirm episodes have summaries: `SELECT COUNT(*) FROM episodes WHERE summary_md IS NOT NULL;`
4. Check CSS inlining: May need email client that supports inline CSS

### Some Channels Missing Recipients

**Issue**: Some channels aren't configured in `channel_recipients`

**Expected**: Those channels use default recipients (fallback)
**To Fix**: Add channel to `channel_recipients` if different recipients desired

## HTML Email Template Customization

The default HTML template includes:

```html
<!-- Header with channel name -->
<h1>{{ channel_name }}</h1>

<!-- Metadata: date range -->
<div class="metadata">...</div>

<!-- Episode count badge -->
<div class="episode-count">
  📺 {{ episode_count }} episode(s) this week
</div>

<!-- Individual episodes -->
{% for episode in episodes %}
<div class="episode">
  <h3>{{ episode.title }}</h3>
  <div class="summary">{{ episode.summary_html|safe }}</div>
  <div class="links">
    <a href="{{ episode.url }}">🎥 Watch on YouTube</a>
    <a href="{{ episode.transcript_path }}">📄 Transcript</a>
  </div>
</div>
{% endfor %}
```

To customize:
1. Edit `templates/channel_digest.html`
2. Modify CSS or structure
3. Keep template variables: `channel_name`, `episodes`, `episode_count`, etc.
4. Test by running: `dbb digest`

## Performance Considerations

**Sending Speed**:
- Separate emails: Slightly slower (one SMTP connection per channel)
- Combined digest: Faster (one connection for all)
- Number of episodes affects rendering time more than mode

**Optimization Tips**:
- Batch email sending: Run digest command once per week
- Use SMTP connection pooling if many recipients
- Keep email recipient lists reasonable

## Email Preview Files

After running `dbb digest`, preview files are saved:

- `digest_preview.html` - Latest generated HTML (for combined mode)
- `digest_preview.txt` - Latest generated plaintext (for combined mode)

**Note**: For separate email mode, previews are not saved per channel (emails are sent directly). To preview, remove `--send` flag first.

## Migration from Combined to Separate

If migrating from combined digest mode:

```yaml
# Old config
send_separate_emails: false
recipients:
  - "everyone@example.com"

# New config - split recipients
send_separate_emails: true
recipients:
  - "default@example.com"  # Fallback
channel_recipients:
  "How I AI":
    - "dev-team@example.com"
  "The AI Daily Brief":
    - "news-team@example.com"
```

Then test with: `dbb digest --send`

## See Also

- [Channel-Specific Prompts](./CHANNEL_SPECIFIC_PROMPTS.md) - Customized summarization
- [Configuration Guide](./CONFIGURATION.md) - Full config reference
- [CLI Commands](../README.md#cli-operations) - All available commands
