# OneDrive Folder Indexer - GitHub Actions

This GitHub Actions workflow allows you to manually index specific OneDrive folders and store the results in your repository.

## 🚀 Features

- **Manual Folder Selection**: Input any folder name from your OneDrive root
- **Append Mode**: Choose to append to existing index files or replace them
- **Depth Control**: Set maximum folder depth to index (useful for large folders)
- **Persistent Storage**: Index files are stored in a dedicated `index-data` branch
- **Statistics Display**: See detailed statistics after indexing completes

## 🎯 How to Use

### 1. Set Up Repository Secrets

Go to your repository **Settings** → **Secrets and variables** → **Actions** and add these secrets:

```
AZURE_CLIENT_ID=your_azure_app_client_id
AZURE_CLIENT_SECRET=your_azure_app_client_secret  
AZURE_TENANT_ID=your_azure_tenant_id
TARGET_USER_ID=target_onedrive_user_email_or_id
```

### 2. Run the Workflow

1. Go to the **Actions** tab in your repository
2. Click on "OneDrive Folder Indexer"
3. Click "Run workflow"
4. Fill in the parameters:

#### Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| **Folder Name** | OneDrive folder name to index | `Sharing` | ✅ Yes |
| **Append Mode** | Append to existing index instead of replacing | `true` | ❌ No |
| **Max Depth** | Maximum folder depth (0 = unlimited) | `0` | ❌ No |

### 3. Example Usage Scenarios

#### Index a New Folder (Replace Mode)
- **Folder Name**: `Documents`
- **Append Mode**: `false`
- **Max Depth**: `0`

This will replace the entire index with just the Documents folder contents.

#### Add Another Folder to Existing Index
- **Folder Name**: `Projects`
- **Append Mode**: `true` 
- **Max Depth**: `3`

This will add the Projects folder (up to 3 levels deep) to your existing index.

#### Index Only Top Level of a Folder
- **Folder Name**: `Archive`
- **Append Mode**: `true`
- **Max Depth**: `1`

This will add only the immediate contents of the Archive folder (no subfolders).

## 📂 Output Files

The workflow creates these files in the `index-data` branch:

- **`file_index.json`**: Complete file and folder structure
- **`index_timestamp.txt`**: Timestamp of last index update

## 🔍 Monitoring Progress

- View real-time logs in the Actions tab while the workflow runs
- Check the summary at the end for statistics
- Download index files as artifacts if needed

## 📊 Index File Structure

The `file_index.json` contains:

```json
{
  "FolderName": [
    {
      "id": "onedrive_item_id",
      "name": "filename.pdf",
      "type": "file",
      "size": 1234567,
      "modified": "2025-01-01T12:00:00Z",
      "path": "FolderName/filename.pdf",
      "download_url": "https://..."
    }
  ]
}
```

## ⚠️ Important Notes

### Append vs Replace Mode

- **Replace Mode** (`append_mode: false`): 
  - Completely replaces the index with just the specified folder
  - Use when you want to start fresh or index only one folder

- **Append Mode** (`append_mode: true`):
  - Adds the new folder to existing index data
  - Use when you want to build a comprehensive index of multiple folders
  - New data overwrites existing data for the same paths

### Depth Limits

- **Max Depth = 0**: No limit (indexes everything)
- **Max Depth = 1**: Only immediate folder contents
- **Max Depth = 2**: Contents + one level of subfolders
- **Max Depth = 3+**: Continues deeper as specified

### Rate Limits

- OneDrive API has rate limits
- Large folders may take several minutes to index
- The workflow has a 60-minute timeout

## 🔧 Advanced Usage

### Indexing Multiple Folders

To build a comprehensive index of multiple folders:

1. **First run** (Replace mode):
   - Folder: `Documents`
   - Append: `false`

2. **Subsequent runs** (Append mode):
   - Folder: `Projects`, Append: `true`
   - Folder: `Archive`, Append: `true`
   - Folder: `Shared`, Append: `true`

### Performance Optimization

For large folders, consider:
- Using depth limits (`max_depth: 2` or `3`)
- Indexing subfolders separately if needed
- Running during off-peak hours

## 🛠️ Troubleshooting

### Common Issues

1. **"Folder not found"**: 
   - Check the exact folder name (case-insensitive)
   - Ensure the folder exists in OneDrive root

2. **"Authentication failed"**:
   - Verify all Azure secrets are correctly set
   - Check Azure app permissions include `Files.Read.All`

3. **"Workflow timeout"**:
   - Try using a smaller max depth
   - Index large folders in smaller chunks

### Getting Help

- Check the workflow logs for detailed error messages
- Verify your Azure app registration has proper permissions
- Ensure the target user has access to the specified folder

## 📈 Best Practices

1. **Start Small**: Test with a small folder first
2. **Use Append Mode**: Build comprehensive indexes incrementally  
3. **Set Reasonable Depths**: Use depth limits for large folder structures
4. **Monitor Usage**: Keep track of OneDrive API usage
5. **Regular Updates**: Re-index folders periodically to catch changes

---

🎉 **Happy Indexing!** This workflow makes it easy to build and maintain comprehensive OneDrive file indexes for your Telegram bot.
