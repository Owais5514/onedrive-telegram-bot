# OneDrive Folder Configuration Guide

This bot can be easily configured to work with different OneDrive folder locations. All configuration is done in the `main.py` file.

## Quick Start

To change the folder that the bot indexes, simply edit the `ONEDRIVE_FOLDERS` list in `main.py`:

```python
# OneDrive folder locations to index
ONEDRIVE_FOLDERS = [
    "Your_Folder_Name",  # Change this to your desired folder name
]
```

## Configuration Options

### ONEDRIVE_FOLDERS
An array of folder names to search for in the OneDrive root directory.

**Examples:**
```python
# Single folder (current default)
ONEDRIVE_FOLDERS = ["Sharing"]

# Multiple folders (future expansion)
ONEDRIVE_FOLDERS = ["Sharing", "Documents", "Public"]

# Different folder name
ONEDRIVE_FOLDERS = ["My_Files"]
```

### FOLDER_CONFIG
Additional configuration options for folder search behavior:

```python
FOLDER_CONFIG = {
    "case_sensitive": False,      # Whether folder names are case-sensitive
    "search_subfolders": False,   # Search in subfolders (not recommended)
    "require_all_folders": False, # Require ALL folders to exist vs ANY
}
```

#### Configuration Details:

- **case_sensitive**: 
  - `False` (default): "sharing", "SHARING", "Sharing" all match
  - `True`: Only exact case matches work

- **search_subfolders**: 
  - `False` (default): Only search in OneDrive root
  - `True`: Search in subfolders (slower, not recommended)

- **require_all_folders**: 
  - `False` (default): Bot works if ANY folder is found
  - `True`: Bot requires ALL folders in the list to exist

## Common Use Cases

### Case 1: Change from "Sharing" to "Documents"
```python
ONEDRIVE_FOLDERS = ["Documents"]
```

### Case 2: Support multiple folders (future feature)
```python
ONEDRIVE_FOLDERS = ["Sharing", "Public", "Downloads"]
```

### Case 3: Case-sensitive folder matching
```python
ONEDRIVE_FOLDERS = ["MyFolder"]
FOLDER_CONFIG = {
    "case_sensitive": True,
    "search_subfolders": False,
    "require_all_folders": False,
}
```

## Important Notes

1. **Restart Required**: After changing configuration, restart the bot for changes to take effect.

2. **Folder Must Exist**: The specified folder(s) must exist in the OneDrive root directory.

3. **Performance**: Keep `search_subfolders` as `False` for better performance.

4. **Future Expansion**: The array structure allows for easy addition of multiple folders in future updates.

## Troubleshooting

### "Target folders not found" error
- Check that the folder name exactly matches (case sensitivity setting)
- Verify the folder exists in OneDrive root directory
- Check the bot logs for available folder names

### Bot not starting
- Ensure the folder configuration is valid Python syntax
- Check that at least one folder name is specified
- Verify your `.env` file is properly configured

## Example Complete Configuration

Here's a complete example of the configuration section in `main.py`:

```python
# =============================================================================
# CONFIGURATION SECTION - EASY TO MODIFY
# =============================================================================

# OneDrive folder locations to index
ONEDRIVE_FOLDERS = [
    "Shared_Files",  # Primary folder for the bot
    # "Archive",     # Uncomment to add additional folders
]

# Configuration for folder search behavior
FOLDER_CONFIG = {
    "case_sensitive": False,      # Case-insensitive matching
    "search_subfolders": False,   # Only search root directory
    "require_all_folders": False, # Work with any available folder
}

# =============================================================================
# END CONFIGURATION SECTION
# =============================================================================
```
