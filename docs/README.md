# OneDrive Telegram Bot - Documentation

## 📚 Quick Start

- **[Main README](../README.md)** - Project overview and setup instructions
- **[Deployment Guide](deployment/RENDER_DEPLOYMENT.md)** - Complete Render deployment walkthrough
- **[Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md)** - Step-by-step deployment verification

## 🚀 Deployment

### Essential Guides
- **[Render Deployment](deployment/RENDER_DEPLOYMENT.md)** - Primary deployment method (recommended)
- **[Database Migration Guide](deployment/DATABASE_MIGRATION_GUIDE.md)** - PostgreSQL setup for persistent storage
- **[Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md)** - Verification steps and troubleshooting

## 🎯 Features

### Available Features
- **[GitHub Actions Indexer](features/GITHUB_ACTIONS_INDEXER.md)** - Manual OneDrive folder indexing workflow
- **[Cold Start Message System](features/COLD_START_MESSAGE_SYSTEM.md)** - Enhanced user experience during bot startup on Render
- **[Cold Start Quick Reference](features/COLD_START_QUICK_REFERENCE.md)** - Quick overview of the cold start system

## 🔧 Development

### Implementation Details
- **[Download Analysis](development/DOWNLOAD_ANALYSIS.md)** - File download optimization analysis
- **[File Index Database Storage](development/FILE_INDEX_DATABASE_STORAGE.md)** - Database persistence implementation
- **[Implementation Summary](development/IMPLEMENTATION_SUMMARY.md)** - Complete implementation overview

## 📁 Documentation Structure

```
docs/
├── README.md                              # This file - documentation index
├── deployment/                            # Deployment guides
│   ├── RENDER_DEPLOYMENT.md              # Primary deployment method
│   ├── DATABASE_MIGRATION_GUIDE.md       # Database setup guide
│   └── DEPLOYMENT_CHECKLIST.md           # Deployment verification
├── features/                              # Feature documentation
│   └── GITHUB_ACTIONS_INDEXER.md         # GitHub Actions workflow
└── development/                           # Implementation details
    ├── DOWNLOAD_ANALYSIS.md               # Download optimization
    ├── FILE_INDEX_DATABASE_STORAGE.md     # Database persistence
    └── IMPLEMENTATION_SUMMARY.md          # Complete implementation

archived/                                  # Historical documentation
├── implementation-docs/                   # Archived implementation docs
├── additional-docs/                       # Alternative deployment docs
└── ...                                   # Other archived files
```

## 🎯 For Different Use Cases

### **New Users / Deployment**
1. [Main README](../README.md) - Start here
2. [Render Deployment Guide](deployment/RENDER_DEPLOYMENT.md) - Deploy your bot
3. [Database Migration Guide](deployment/DATABASE_MIGRATION_GUIDE.md) - Set up persistent storage

### **Development / Customization**
1. [Implementation Summary](development/IMPLEMENTATION_SUMMARY.md) - Understand the architecture
2. [Download Analysis](development/DOWNLOAD_ANALYSIS.md) - File handling details
3. [File Index Database Storage](development/FILE_INDEX_DATABASE_STORAGE.md) - Database implementation

### **Advanced Features**
1. [GitHub Actions Indexer](features/GITHUB_ACTIONS_INDEXER.md) - Automated indexing
2. [Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md) - Production deployment

## 📋 Archive Information

Historical implementation documentation has been moved to `archived/implementation-docs/` to keep the main documentation clean and focused. These archived docs contain detailed development history but are not needed for deployment or daily usage.

## 🔗 External Resources

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Telegram Bot API**: [core.telegram.org/bots/api](https://core.telegram.org/bots/api)
- **Microsoft Graph API**: [docs.microsoft.com/graph](https://docs.microsoft.com/graph)
