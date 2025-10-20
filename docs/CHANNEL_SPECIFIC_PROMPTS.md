# Channel-Specific Summarization Prompts

This document explains how to configure and use channel-specific prompts for customized episode summarization.

## Overview

The summarization system supports custom prompts tailored to specific YouTube channels. Each channel can have its own summarization prompt that defines how episodes should be analyzed and summarized.

- **Default Prompt**: `./prompts/default_prompt.md` - Used for channels without specific configuration
- **Channel-Specific Prompts**: Defined in `config.yaml` under `summarize.channel_prompts`

## How It Works

1. When summarizing an episode, the system checks if the channel has a specific prompt configured
2. If a channel-specific prompt exists, it uses that prompt
3. If no channel-specific prompt is configured, it falls back to the default prompt
4. Prompts are cached in memory after the first use for performance

## Configuration

### Adding Channel-Specific Prompts

In `config.yaml`, add channel-specific prompts to the `channel_prompts` dictionary:

```yaml
summarize:
  ollama_host: "http://localhost:11434"
  ollama_model: "gemma3:latest"
  prompt_path: "./prompts/default_prompt.md"  # Default for all channels

  # Channel-specific prompts (key must match channel_title exactly)
  channel_prompts:
    "How I AI": "./prompts/how_i_ai_prompt.md"
    "The AI Daily Brief: Artificial Intelligence News Podcast": "./prompts/ai_daily_brief_prompt.md"

  timeout_s: 300
  retry_attempts: 3
```

**Important**: The channel name key must match the exact `channel_title` stored in the database.

## Current Channel Configurations

### 1. How I AI
- **Channel**: "How I AI"
- **Prompt**: `./prompts/how_i_ai_prompt.md`
- **Focus**: AI product development strategy, debugging, QA, and systematic improvement

**Structure**:
- Problem Solved
- Technologies Used
- Workflow Laid Out Step by Step
- Strategies Used to Solve (Key Methodologies)
- How to Think Agentically

### 2. The AI Daily Brief: Artificial Intelligence News Podcast
- **Channel**: "The AI Daily Brief: Artificial Intelligence News Podcast"
- **Prompt**: `./prompts/ai_daily_brief_prompt.md`
- **Focus**: News and updates with practical insights and clear takeaways

**Structure**:
- 🔍 Core Breakdown: Key Ideas & Takeaways
- 💡 Deep Dive: For Each Key Idea
- ✅ Wrap-Up

## Creating a New Channel-Specific Prompt

### Step 1: Identify the Channel Name

Check your database to find the exact channel name:

```bash
duckdb dbb.duckdb
SELECT DISTINCT channel_title FROM episodes;
```

### Step 2: Create the Prompt File

Create a new markdown file in the `prompts/` directory:

```bash
touch prompts/my_channel_prompt.md
```

### Step 3: Write the Prompt

Create a prompt template that includes `{transcript}` placeholder:

```markdown
# My Channel Summary Prompt

## Instructions

Analyze the podcast transcript and create a summary with:

1. **Main Topic**: What is this episode about?
2. **Key Insights**: List the top 5 takeaways
3. **Actionable Items**: What should listeners do?

---

## TRANSCRIPT

{transcript}

## SUMMARY
```

### Step 4: Update config.yaml

Add your channel to the `channel_prompts` section:

```yaml
channel_prompts:
  "My Channel Name": "./prompts/my_channel_prompt.md"
```

**Important**: The channel name key must match exactly with the `channel_title` in your database.

## Prompt Template Guidelines

### Required Elements

All prompt files must include:
1. `{transcript}` placeholder - This will be replaced with the actual transcript
2. Clear instructions for the LLM about what to summarize
3. Expected output format (markdown sections, bullet points, etc.)

### Optional Elements

- Section headers to organize the summary
- Specific focus areas or areas to prioritize
- Examples of desired output format
- Instructions for handling special cases

### Best Practices

1. **Be specific**: The more specific your instructions, the better the results
2. **Use markdown formatting**: Demonstrate the expected output format
3. **Keep it concise**: Long prompts don't necessarily produce better results
4. **Test iteratively**: Try your prompt and refine based on results

## Testing Channel-Specific Prompts

### Test Configuration Loading

Verify that your channel prompt configuration is loaded correctly:

```python
from dbb.config import load_config

cfg = load_config("config.yaml")
for channel, path in cfg.summarize.channel_prompts.items():
    print(f"{channel} → {path}")
```

### Test Prompt File Loading

Ensure prompt files are found and loaded:

```bash
dbb summarize --recent 1
```

Check the logs for messages like:
```
Using channel-specific prompt for 'How I AI'
Loaded prompt template from ./prompts/how_i_ai_prompt.md
```

### Manual Testing

To test a specific prompt with a transcript:

```python
from dbb.config import load_config
from dbb.summarize import SummarizerManager

cfg = load_config("config.yaml")
summarizer = SummarizerManager(cfg)

# Load a transcript from file or database
transcript = "..."

# Generate summary with channel name
summary = summarizer.summarize(transcript, channel_name="How I AI")
print(summary)
```

## Troubleshooting

### Prompt Not Being Used

**Issue**: Your channel-specific prompt isn't being used

**Solution**:
1. Check that the channel name in `config.yaml` matches the `channel_title` in the database exactly (case-sensitive)
2. Verify the prompt file path is correct and the file exists
3. Check logs for errors: `log_level: DEBUG` in config.yaml
4. Reload the configuration (restart the application)

### Prompt File Not Found

**Issue**: Error "Prompt template not found"

**Solution**:
1. Verify the prompt file path is relative to the project root
2. Check file permissions: `ls -la prompts/your_prompt.md`
3. Ensure the file extension is `.md`

### Channel Name Mismatch

**Issue**: Summaries still use default prompt

**Solution**:
1. Check the exact channel name in database: `SELECT DISTINCT channel_title FROM episodes;`
2. Copy the exact channel name (including spaces, punctuation, capitalization)
3. Update config.yaml with the exact channel name
4. Restart the application

## Advanced: Custom Prompt Strategies

### Strategy 1: Specialized Domains

Create prompts for specific content domains:

```yaml
channel_prompts:
  "AI Research Weekly": "./prompts/research_focused_prompt.md"
  "AI News Roundup": "./prompts/news_focused_prompt.md"
  "AI Tutorial Series": "./prompts/tutorial_focused_prompt.md"
```

### Strategy 2: Prompt Evolution

Keep multiple versions of prompts as you refine them:

```
prompts/
├── how_i_ai_prompt.md          (current version)
├── how_i_ai_prompt_v1.md       (older version)
├── how_i_ai_prompt_experiment.md  (testing new format)
```

### Strategy 3: Channel Group Prompts

If multiple channels have similar content, create a shared prompt:

```yaml
channel_prompts:
  "AI Podcast 1": "./prompts/podcast_format_prompt.md"
  "AI Podcast 2": "./prompts/podcast_format_prompt.md"
  "AI Podcast 3": "./prompts/podcast_format_prompt.md"
```

## Performance Considerations

- **Prompt Caching**: Prompts are cached after first use to improve performance
- **Prompt Size**: Larger prompts consume more tokens. Keep them focused and concise
- **Context Length**: Very long prompts leave less room for the transcript. Aim for 500-1000 word prompts

## Default Prompt Fallback

If any channel-specific prompt fails to load or the channel isn't configured:

1. A warning is logged
2. The default prompt (`prompt_path`) is used
3. Summarization continues normally

This ensures summarization always works, even with missing configuration.

## See Also

- [Configuration Guide](./CONFIGURATION.md) - Full configuration reference
- [CLI Commands](../README.md#cli-operations) - How to run summarization
- [Database Schema](./DATABASE.md) - Understanding the episodes table
