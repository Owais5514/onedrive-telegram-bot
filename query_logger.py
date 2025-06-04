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
        
        # Track changes since last commit
        self.changes_since_commit = False
        self.last_commit_time = datetime.now()
        
        # Background commit task
        self.commit_task = None
        
        # Load existing queries if file exists
        self._load_existing_queries()
        
        # Initialize git if needed
        self._init_git()
        
        # Start periodic commit task
        self.start_periodic_commits()
    
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
            
            # Always ensure git user identity is set for logging commits
            subprocess.run(['git', 'config', 'user.name', 'OneDrive Bot Logger'], check=True, cwd='.')
            subprocess.run(['git', 'config', 'user.email', 'bot@onedrive-telegram.local'], check=True, cwd='.')
            logger.info("Git user identity configured for query logging")
            
        except Exception as e:
            logger.warning(f"Git initialization failed: {e}")
    
    def log_query(self, user_id: int, username: str, query: str, query_type: str = "browse") -> bool:
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
            
            # Mark that there are changes since last commit
            self.changes_since_commit = True
            
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
        
        if query_type == "browse_folder":
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
        elif query_type in ["browse_start"]:
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"🎯 START - User: {query_entry['username']} ({query_entry['user_id']}) | "
                f"Type: {query_entry['query_type']} | "
                f"Query: {query_entry['query']}\n"
            )
        else:
            log_line = (
                f"[{query_entry['date']} {query_entry['time']}] "
                f"❓ OTHER - User: {query_entry['username']} ({query_entry['user_id']}) | "
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
        """Commit log files to git logs branch without switching working directory"""
        try:
            # Store current branch
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                                 capture_output=True, text=True, cwd='.')
            current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else "main"
            
            # Create logs branch if it doesn't exist
            subprocess.run(['git', 'branch', 'logs'], capture_output=True, cwd='.')
            
            # Add files to staging area
            subprocess.run(['git', 'add', '-f', self.log_file, self.json_file], capture_output=True, cwd='.')
            
            # Create commit message
            commit_msg = (
                f"Log query from {query_entry['username']} "
                f"({query_entry['date']} {query_entry['time']})"
            )
            
            # Commit to logs branch without checkout using git commit-tree
            # First, get the current tree
            tree_result = subprocess.run(['git', 'write-tree'], capture_output=True, text=True, cwd='.')
            if tree_result.returncode != 0:
                raise Exception("Failed to write tree")
            
            tree_hash = tree_result.stdout.strip()
            
            # Get logs branch HEAD (if exists)
            logs_head_result = subprocess.run(['git', 'rev-parse', 'logs'], 
                                            capture_output=True, text=True, cwd='.')
            
            # Set git author/committer environment for commit-tree
            git_env = os.environ.copy()
            git_env.update({
                'GIT_AUTHOR_NAME': 'OneDrive Bot Logger',
                'GIT_AUTHOR_EMAIL': 'bot@onedrive-telegram.local',
                'GIT_COMMITTER_NAME': 'OneDrive Bot Logger',
                'GIT_COMMITTER_EMAIL': 'bot@onedrive-telegram.local'
            })
            
            # Create commit
            if logs_head_result.returncode == 0:
                # Logs branch exists, commit with parent
                logs_head = logs_head_result.stdout.strip()
                commit_result = subprocess.run(['git', 'commit-tree', tree_hash, '-p', logs_head, '-m', commit_msg],
                                             capture_output=True, text=True, env=git_env, cwd='.')
            else:
                # First commit to logs branch
                commit_result = subprocess.run(['git', 'commit-tree', tree_hash, '-m', commit_msg],
                                             capture_output=True, text=True, env=git_env, cwd='.')
            
            if commit_result.returncode != 0:
                raise Exception(f"Failed to create commit: {commit_result.stderr}")
            
            commit_hash = commit_result.stdout.strip()
            
            # Update logs branch to point to new commit
            subprocess.run(['git', 'branch', '-f', 'logs', commit_hash], check=True, cwd='.')
            
            logger.info(f"Query logged and committed to git logs branch (staying on {current_branch})")
            
        except subprocess.CalledProcessError as e:
            logger.debug(f"Git commit failed (might be no changes): {e}")
        except Exception as e:
            logger.warning(f"Git commit error: {e}")
    
    def start_periodic_commits(self):
        """Start background task for periodic git commits"""
        try:
            if asyncio.get_event_loop().is_running():
                # If there's already a running event loop, schedule the task
                self.commit_task = asyncio.create_task(self._periodic_commit_loop())
                logger.info("Started periodic commit task (every 60 seconds)")
            else:
                logger.info("No event loop running, periodic commits will be manual")
        except Exception as e:
            logger.warning(f"Could not start periodic commits: {e}")
    
    async def _periodic_commit_loop(self):
        """Background loop that commits logs every minute"""
        while True:
            try:
                await asyncio.sleep(60)  # Wait 60 seconds
                
                # Check if there are changes to commit
                if self.changes_since_commit:
                    await self._async_git_commit_if_changes()
                    self.changes_since_commit = False
                    self.last_commit_time = datetime.now()
                    logger.info("Periodic git commit completed")
                    
            except asyncio.CancelledError:
                logger.info("Periodic commit task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic commit loop: {e}")
                # Continue the loop even if there's an error
                await asyncio.sleep(10)  # Short delay before retrying
    
    async def _async_git_commit_if_changes(self):
        """Async wrapper for git commit with change detection"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._git_commit_if_changes)
        except Exception as e:
            logger.error(f"Async git commit failed: {e}")
    
    def _git_commit_if_changes(self):
        """Commit logs to git if there are changes since last commit"""
        try:
            # Check if log files exist and have content
            if not (os.path.exists(self.log_file) and os.path.exists(self.json_file)):
                return
                
            # Check file modification times
            log_mtime = os.path.getmtime(self.log_file)
            json_mtime = os.path.getmtime(self.json_file)
            last_commit_timestamp = self.last_commit_time.timestamp()
            
            if log_mtime <= last_commit_timestamp and json_mtime <= last_commit_timestamp:
                return  # No changes since last commit
            
            # Store current branch
            current_branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                                 capture_output=True, text=True, cwd='.')
            current_branch = current_branch_result.stdout.strip() if current_branch_result.returncode == 0 else "main"
            
            # Create logs branch if it doesn't exist
            subprocess.run(['git', 'branch', 'logs'], capture_output=True, cwd='.')
            
            # Add files to staging area (force add to bypass .gitignore)
            subprocess.run(['git', 'add', '-f', self.log_file, self.json_file], capture_output=True, cwd='.')
            
            # Check if there are actually staged changes
            diff_result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True, cwd='.')
            if diff_result.returncode == 0:
                return  # No changes to commit
            
            # Create commit message with timestamp
            commit_msg = f"Periodic log commit - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            # Get the current tree
            tree_result = subprocess.run(['git', 'write-tree'], capture_output=True, text=True, cwd='.')
            if tree_result.returncode != 0:
                raise Exception("Failed to write tree")
            
            tree_hash = tree_result.stdout.strip()
            
            # Get logs branch HEAD (if exists)
            logs_head_result = subprocess.run(['git', 'rev-parse', 'logs'], 
                                            capture_output=True, text=True, cwd='.')
            
            # Set git author/committer environment for commit-tree
            git_env = os.environ.copy()
            git_env.update({
                'GIT_AUTHOR_NAME': 'OneDrive Bot Logger',
                'GIT_AUTHOR_EMAIL': 'bot@onedrive-telegram.local',
                'GIT_COMMITTER_NAME': 'OneDrive Bot Logger',
                'GIT_COMMITTER_EMAIL': 'bot@onedrive-telegram.local'
            })
            
            # Create commit
            if logs_head_result.returncode == 0:
                # Logs branch exists, commit with parent
                logs_head = logs_head_result.stdout.strip()
                commit_result = subprocess.run(['git', 'commit-tree', tree_hash, '-p', logs_head, '-m', commit_msg],
                                             capture_output=True, text=True, env=git_env, cwd='.')
            else:
                # First commit to logs branch
                commit_result = subprocess.run(['git', 'commit-tree', tree_hash, '-m', commit_msg],
                                             capture_output=True, text=True, env=git_env, cwd='.')
            
            if commit_result.returncode != 0:
                raise Exception(f"Failed to create commit: {commit_result.stderr}")
            
            commit_hash = commit_result.stdout.strip()
            
            # Update logs branch to point to new commit
            subprocess.run(['git', 'branch', '-f', 'logs', commit_hash], check=True, cwd='.')
            
            logger.info(f"Periodic commit created: {commit_hash[:8]} (staying on {current_branch})")
            
        except subprocess.CalledProcessError as e:
            logger.debug(f"Periodic git commit failed (might be no changes): {e}")
        except Exception as e:
            logger.warning(f"Periodic git commit error: {e}")
    
    def stop_periodic_commits(self):
        """Stop the periodic commit task"""
        if self.commit_task and not self.commit_task.done():
            self.commit_task.cancel()
            logger.info("Stopped periodic commit task")

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
    
    def final_commit_and_push(self):
        """Final commit of any pending logs and attempt to push to remote (for GitHub Actions)"""
        try:
            # Do a final commit of any changes
            if self.changes_since_commit:
                self._git_commit_if_changes()
                self.changes_since_commit = False
                logger.info("Final commit of pending logs completed")
            
            # In GitHub Actions, also attempt to push the logs branch
            # This is safe to call even in local environments - will just fail silently
            try:
                # Check if we have git remotes (indicates we're in a repository with remotes)
                remote_result = subprocess.run(['git', 'remote'], capture_output=True, text=True, cwd='.')
                if remote_result.returncode == 0 and remote_result.stdout.strip():
                    # Try to push logs branch to origin
                    push_result = subprocess.run(['git', 'push', 'origin', 'logs'], 
                                               capture_output=True, text=True, cwd='.')
                    if push_result.returncode == 0:
                        logger.info("Logs branch pushed to remote repository")
                    else:
                        # Try force push as fallback
                        force_push_result = subprocess.run(['git', 'push', 'origin', 'logs', '--force'], 
                                                         capture_output=True, text=True, cwd='.')
                        if force_push_result.returncode == 0:
                            logger.info("Logs branch force-pushed to remote repository")
                        else:
                            logger.debug(f"Could not push logs branch: {force_push_result.stderr}")
                            
            except Exception as e:
                logger.debug(f"Remote push not available or failed: {e}")
                
        except Exception as e:
            logger.warning(f"Final commit failed: {e}")

# Global logger instance
query_logger = QueryLogger()

async def log_user_query(user_id: int, username: str, query: str, query_type: str = "browse"):
    """Async wrapper for logging queries"""
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, query_logger.log_query, user_id, username, query, query_type)
    except Exception as e:
        logger.error(f"Async query logging failed: {e}")
        return False
