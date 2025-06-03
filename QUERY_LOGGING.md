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
- Bot runs from `main` branch (normal operation)
- Logs are automatically committed to `logs` branch (separate from main code)
- Working directory stays on `main` - no branch switching during bot operation
- Uses advanced git commands (`commit-tree`) to commit to logs branch without checkout
- Each commit includes the user and timestamp information
- Git repository is auto-initialized if needed
- Log files are force-added to bypass `.gitignore` restrictions

### 🔧 **Git Identity Configuration**
The query logger automatically configures git identity for proper commit attribution:
- **Author:** OneDrive Bot Logger <bot@onedrive-telegram.local>
- **Committer:** OneDrive Bot Logger <bot@onedrive-telegram.local>
- Sets both repository-level config and environment variables
- Ensures commits work even in containerized environments

**Fixed Issue:** Previously git commits failed with "Author identity unknown" error. Now resolved with proper identity setup in both `_init_git()` and commit environment variables.

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

## ✅ **FIXED: Proper Branch Management**

**Problem Solved:** The bot now correctly:
- ✅ **Runs from `main` branch** (stable bot code)
- ✅ **Commits logs to `logs` branch** (separate log history)  
- ✅ **Never switches working directory** (maintains stability)

**Technical Implementation:**
- Uses `git commit-tree` for direct branch commits
- Force-adds log files with `-f` flag to bypass `.gitignore`
- Creates `logs` branch automatically if needed
- No `git checkout` commands that could disrupt bot operation

**Production Status:** The query logger is now fully operational and providing valuable insights into how users interact with both the AI search and browse files features of the bot!
