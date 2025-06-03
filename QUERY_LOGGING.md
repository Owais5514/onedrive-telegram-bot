# Query Logger Implementation

## Overview
The OneDrive Telegram Bot now includes comprehensive query logging that tracks all user interactions and automatically commits logs to git in real-time.

## Features

### 🎯 Comprehensive Logging
The bot logs the following user activities:

1. **AI Search Activities:**
   - `ai_search_start` - When user clicks AI search button
   - `ai_search` - The actual search query submitted
   - `ai_search_result` - Summary of search results returned

2. **File Browsing Activities:**
   - `browse_start` - When user starts browsing files
   - `browse_folder` - Each folder navigation action

3. **File Interactions:**
   - `file_view` - When user views file details
   - `file_download` - When user successfully downloads a file

### 📁 Log Files
Two log files are created:

1. **`beta_test_queries.log`** - Human-readable format with emojis
2. **`beta_test_queries.json`** - Machine-readable JSON format

### 🎨 Readable Log Format
The readable log uses emojis and clear formatting:

```
[2025-06-03 08:39:14] 🤖 AI SEARCH - User: owais5514 (5759568708) | Query: "Math quiz files"
[2025-06-03 08:39:16] 📊 AI RESULT - User: owais5514 (5759568708) | Result: AI search 'Math quiz files' returned 8 files and 8 folders
[2025-06-03 08:39:18] 📁 BROWSE - User: owais5514 (5759568708) | Action: Browsed folder: MATH 1203 (path: 1st Year 2nd Semester/Books/MATH 1203)
[2025-06-03 08:39:22] ⬇️ DOWNLOAD - User: owais5514 (5759568708) | Action: Downloaded file: lecture1.pdf (2.3MB) from /Mathematics
```

### 🔄 Git Integration
- Logs are automatically committed to git after each entry
- Each commit includes the user and timestamp information
- Git repository is auto-initialized if needed

## Implementation Details

### Code Integration
The logging is seamlessly integrated into `bot.py`:

```python
from query_logger import log_user_query

# Example usage in bot methods:
await log_user_query(user_id, username, user_query, "ai_search")
await log_user_query(user_id, username, browse_action, "browse_folder")
await log_user_query(user_id, username, download_action, "file_download")
```

### Logging Locations
Query logging is integrated at these key points:

1. **AI Search Flow:**
   - Button click → `ai_search_start`
   - Query submission → `ai_search`
   - Results display → `ai_search_result`

2. **Browse Files Flow:**
   - Browse button click → `browse_start`
   - Each folder navigation → `browse_folder`
   - File detail view → `file_view`
   - Successful download → `file_download`

### Error Handling
- Logging failures are handled gracefully with warnings
- Bot functionality continues even if logging fails
- Each logging call is wrapped in try-catch blocks

## Statistics and Analytics

The query logger provides built-in analytics:

```python
stats = query_logger.get_stats()
# Returns: total_queries, unique_users, query_types breakdown
```

Daily summaries can be exported:
```python
summary = query_logger.export_daily_summary("2025-06-03")
```

## Benefits

1. **Usage Analytics** - Track how users interact with the bot
2. **Feature Performance** - Monitor AI search vs browse usage
3. **User Behavior** - Understand navigation patterns
4. **Debugging** - Historical logs help troubleshoot issues
5. **Git History** - Version control for all user activities
6. **Real-time Insights** - Live monitoring of bot usage

## Production Ready
- Async logging doesn't block bot operations
- Efficient file I/O with error handling
- Git commits are batched per query
- Readable format for human analysis
- JSON format for automated processing

The query logger is now actively logging all user interactions in both AI search and browse files workflows, providing comprehensive insights into bot usage patterns.
