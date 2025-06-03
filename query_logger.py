#!/usr/bin/env python3
"""
Query Logger - Logs user queries and commits to git in real time
Simple implementation for beta testing
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

class QueryLogger:
    def __init__(self, log_file: str = "beta_test_queries.log", json_file: str = "beta_test_queries.json"):
        self.log_file = log_file
        self.json_file = json_file
        self.queries_data = []
        
        # Load existing queries if file exists
        self._load_existing_queries()
        
        # Initialize git if needed
        self._init_git()
    
    def _load_existing_queries(self):
        """Load existing queries from JSON file"""
        try:
            if os.path.exists(self.json_file):
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    self.queries_data = json.load(f)
                logger.info(f"Loaded {len(self.queries_data)} existing queries")
        except Exception as e:
            logger.warning(f"Could not load existing queries: {e}")
            self.queries_data = []
    
    def _init_git(self):
        """Initialize git repository if not already initialized"""
        try:
            # Check if we're in a git repo
            result = subprocess.run(['git', 'status'], capture_output=True, text=True, cwd='.')
            if result.returncode != 0:
                # Initialize git repo
                subprocess.run(['git', 'init'], check=True, cwd='.')
                subprocess.run(['git', 'config', 'user.name', 'OneDrive Bot Logger'], check=True, cwd='.')
                subprocess.run(['git', 'config', 'user.email', 'bot@onedrive-telegram.local'], check=True, cwd='.')
                logger.info("Initialized git repository for query logging")
        except Exception as e:
            logger.warning(f"Git initialization failed: {e}")
    
    def log_query(self, user_id: int, username: str, query: str, query_type: str = "ai_search") -> bool:
        """Log a user query with timestamp"""
        try:
            timestamp = datetime.now()
            
            # Create query entry
            query_entry = {
                "timestamp": timestamp.isoformat(),
                "user_id": user_id,
                "username": username,
                "query": query,
                "query_type": query_type,
                "date": timestamp.strftime("%Y-%m-%d"),
                "time": timestamp.strftime("%H:%M:%S")
            }
            
            # Add to in-memory list
            self.queries_data.append(query_entry)
            
            # Write human-readable log
            self._write_readable_log(query_entry)
            
            # Write JSON log
            self._write_json_log()
            
            # Commit to git
            self._git_commit(query_entry)
            
            logger.info(f"Logged query from user {username} ({user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log query: {e}")
            return False
    
    def _write_readable_log(self, query_entry: dict):
        """Write human-readable log entry"""
        # Format different query types differently for better readability
        query_type = query_entry['query_type']
        
        if query_type == "ai_search":
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"🤖 AI SEARCH - User: {query_entry['username']} ({query_entry['user_id']}) | "
                f"Query: \"{query_entry['query']}\"\n"
            )
        elif query_type == "ai_search_result":
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"📊 AI RESULT - User: {query_entry['username']} ({query_entry['user_id']}) | "
                f"Result: {query_entry['query']}\n"
            )
        elif query_type == "browse_folder":
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"📁 BROWSE - User: {query_entry['username']} ({query_entry['user_id']}) | "
                f"Action: {query_entry['query']}\n"
            )
        elif query_type == "file_view":
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"👁️ VIEW - User: {query_entry['username']} ({query_entry['user_id']}) | "
                f"Action: {query_entry['query']}\n"
            )
        elif query_type == "file_download":
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"⬇️ DOWNLOAD - User: {query_entry['username']} ({query_entry['user_id']}) | "
                f"Action: {query_entry['query']}\n"
            )
        elif query_type in ["ai_search_start", "browse_start"]:
            icon = "🤖" if "ai" in query_type else "📁"
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"{icon} START - User: {query_entry['username']} ({query_entry['user_id']}) | "
                f"Action: {query_entry['query']}\n"
            )
        else:
            # Default format for other types
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"User: {query_entry['username']} ({query_entry['user_id']}) | "
                f"Type: {query_entry['query_type']} | "
                f"Query: {query_entry['query']}\n"
            )
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line)
    
    def _write_json_log(self):
        """Write complete JSON log"""
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.queries_data, f, indent=2, ensure_ascii=False)
    
    def _git_commit(self, query_entry: dict):
        """Commit log files to git"""
        try:
            # Add files to git
            subprocess.run(['git', 'add', self.log_file, self.json_file], check=True, cwd='.')
            
            # Create commit message
            commit_msg = (
                f"Log query from {query_entry['username']} "
                f"({query_entry['date']} {query_entry['time']})"
            )
            
            # Commit
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True, cwd='.')
            
            logger.info("Query logged and committed to git")
            
        except subprocess.CalledProcessError as e:
            # Might fail if no changes or git issues - that's okay
            logger.debug(f"Git commit failed (might be no changes): {e}")
        except Exception as e:
            logger.warning(f"Git commit error: {e}")
    
    def get_stats(self) -> dict:
        """Get query statistics"""
        if not self.queries_data:
            return {"total_queries": 0, "unique_users": 0, "query_types": {}}
        
        unique_users = len(set(q["user_id"] for q in self.queries_data))
        query_types = {}
        
        for query in self.queries_data:
            qtype = query.get("query_type", "unknown")
            query_types[qtype] = query_types.get(qtype, 0) + 1
        
        return {
            "total_queries": len(self.queries_data),
            "unique_users": unique_users,
            "query_types": query_types,
            "latest_query": self.queries_data[-1]["timestamp"] if self.queries_data else None
        }
    
    def export_daily_summary(self, date: str = None) -> str:
        """Export daily summary"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        daily_queries = [q for q in self.queries_data if q["date"] == date]
        
        if not daily_queries:
            return f"No queries found for {date}"
        
        summary = f"\n=== DAILY SUMMARY FOR {date} ===\n"
        summary += f"Total Queries: {len(daily_queries)}\n"
        summary += f"Unique Users: {len(set(q['user_id'] for q in daily_queries))}\n\n"
        
        summary += "QUERIES:\n"
        for i, query in enumerate(daily_queries, 1):
            summary += (
                f"{i}. [{query['time']}] {query['username']}: "
                f"{query['query'][:100]}{'...' if len(query['query']) > 100 else ''}\n"
            )
        
        return summary

# Global logger instance
query_logger = QueryLogger()

async def log_user_query(user_id: int, username: str, query: str, query_type: str = "ai_search"):
    """Async wrapper for logging queries"""
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, query_logger.log_query, user_id, username, query, query_type)
    except Exception as e:
        logger.error(f"Async query logging failed: {e}")
        return False
