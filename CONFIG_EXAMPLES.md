# Configuration Examples for OneDrive Telegram Bot

This file contains practical examples of how to configure the bot for different OneDrive folder setups.

## Example 1: Change from "Sharing" to "Documents" folder

Edit the `main.py` file and change:

```python
# FROM:
ONEDRIVE_FOLDERS = [
    "Sharing",  # Default folder
]

# TO:
ONEDRIVE_FOLDERS = [
    "Documents",  # Your documents folder
]
```

## Example 2: Use a custom folder name like "Bot_Files"

```python
ONEDRIVE_FOLDERS = [
    "Bot_Files",  # Custom folder name
]
```

## Example 3: Case-sensitive folder matching

If your folder is named exactly "MyFolder" and you want exact matching:

```python
ONEDRIVE_FOLDERS = [
    "MyFolder",  # Must match exactly
]

FOLDER_CONFIG = {
    "case_sensitive": True,     # Exact case matching required
    "search_subfolders": False,
    "require_all_folders": False,
}
```

## Example 4: Prepare for multiple folders (future feature)

To prepare for future support of multiple folders:

```python
ONEDRIVE_FOLDERS = [
    "Sharing",      # Primary folder (currently used)
    "Documents",    # Future: additional folder
    "Archive",      # Future: additional folder
]

# Note: Currently only the first folder is used, but this structure
# allows for easy expansion when multi-folder support is added
```

## Example 5: Different folder structure organizations

### For Personal Use:
```python
ONEDRIVE_FOLDERS = [
    "Personal_Files",
]
```

### For Team/Company Use:
```python
ONEDRIVE_FOLDERS = [
    "Team_Resources",
]
```

### For Educational Use:
```python
ONEDRIVE_FOLDERS = [
    "Course_Materials",
]
```

## Quick Setup Steps

1. **Backup your current `main.py`** (recommended)
2. **Edit the configuration section** in `main.py`
3. **Save the file**
4. **Restart the bot**
5. **Test by running** `/start` in Telegram

## Verification Steps

After changing the configuration:

1. Check the bot logs when starting - it should show:
   ```
   Configured to search for folders: ['Your_Folder_Name']
   ```

2. If the folder is found, you'll see:
   ```
   Found target folder: Your_Folder_Name
   ```

3. If the folder is not found, you'll see available folders:
   ```
   Available folders: ['Folder1', 'Folder2', 'Folder3']
   ```

## Troubleshooting

### "None of the target folders found" Error

This means the folder name doesn't exist in your OneDrive root. 

**Solutions:**
1. Check the exact folder name in OneDrive
2. Verify case sensitivity settings
3. Create the folder in OneDrive if it doesn't exist
4. Check the bot logs for available folder names

### Folder exists but bot can't find it

**Check:**
1. Folder is in OneDrive **root directory** (not in a subfolder)
2. Case sensitivity setting matches your folder name
3. No special characters or spaces causing issues

### Bot starts but shows no files

**Possible causes:**
1. Folder exists but is empty
2. Permission issues with the Azure app registration
3. OneDrive sync issues

**Solutions:**
1. Add some test files to the folder
2. Check Azure app permissions include `Files.Read.All`
3. Wait for OneDrive sync to complete

## Advanced Configuration

### Future: Multiple Folder Support
When multi-folder support is added, the bot will be able to index and provide access to multiple folders simultaneously.

**Prepared Configuration:**
```python
ONEDRIVE_FOLDERS = [
    "Primary_Folder",    # Main folder
    "Secondary_Folder",  # Additional folder
    "Archive_Folder",    # Archive folder
]

FOLDER_CONFIG = {
    "case_sensitive": False,
    "search_subfolders": False,
    "require_all_folders": True,  # Require ALL folders to exist
}
```

This structure ensures your bot is ready for future enhancements while working perfectly with the current single-folder implementation.
