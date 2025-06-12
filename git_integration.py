#!/usr/bin/env python3
"""
Git Integration Module for OneDrive Bot
Handles committing index files back to the repository when running in GitHub Actions
"""

import os
import subprocess
import logging
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)

class GitIndexManager:
    """Handles Git operations for index file persistence"""
    
    def __init__(self):
        self.is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        self.is_git_repo = self._check_git_repo()
        
    def _check_git_repo(self) -> bool:
        """Check if we're in a Git repository"""
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], 
                         check=True, capture_output=True, text=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _run_git_command(self, cmd: List[str]) -> Optional[str]:
        """Run a git command and return output"""
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)}, Error: {e}")
            return None
        except FileNotFoundError:
            logger.error("Git not found in PATH")
            return None
    
    def configure_git(self):
        """Configure Git for automated commits"""
        if not self.is_git_repo:
            logger.warning("Not in a Git repository, skipping Git configuration")
            return False
            
        # Configure Git identity for automated commits
        commands = [
            ['git', 'config', 'user.name', 'OneDrive Bot Auto-Indexer'],
            ['git', 'config', 'user.email', 'indexer@onedrive-telegram-bot.local'],
            ['git', 'config', 'commit.gpgsign', 'false'],  # Disable GPG signing
        ]
        
        for cmd in commands:
            if self._run_git_command(cmd) is None:
                logger.error(f"Failed to configure Git: {' '.join(cmd)}")
                return False
                
        logger.info("Git configured for automated commits")
        return True
    
    def commit_index_files(self, files: List[str]) -> bool:
        """Commit index files to the repository"""
        if not self.is_git_repo:
            logger.warning("Not in a Git repository, cannot commit index files")
            return False
            
        if not self.is_github_actions:
            logger.info("Not running in GitHub Actions, skipping index commit")
            return False
            
        try:
            # Check if files exist
            existing_files = [f for f in files if os.path.exists(f)]
            if not existing_files:
                logger.warning("No index files found to commit")
                return False
            
            # Configure Git
            if not self.configure_git():
                return False
            
            # Add files
            add_cmd = ['git', 'add'] + existing_files
            if self._run_git_command(add_cmd) is None:
                logger.error("Failed to add index files to Git")
                return False
            
            # Check if there are changes to commit
            status_output = self._run_git_command(['git', 'status', '--porcelain'])
            if not status_output:
                logger.info("No changes to commit for index files")
                return True
            
            # Create commit message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            commit_msg = f"Update OneDrive index files - {timestamp}"
            
            # Commit changes
            commit_cmd = ['git', 'commit', '-m', commit_msg]
            if self._run_git_command(commit_cmd) is None:
                logger.error("Failed to commit index files")
                return False
            
            logger.info(f"Index files committed: {', '.join(existing_files)}")
            
            # Try to push if we're in GitHub Actions
            if self.is_github_actions:
                return self._push_to_remote()
            
            return True
            
        except Exception as e:
            logger.error(f"Error committing index files: {e}")
            return False
    
    def _push_to_remote(self) -> bool:
        """Push changes to remote repository"""
        try:
            # Get current branch
            current_branch = self._run_git_command(['git', 'branch', '--show-current'])
            if not current_branch:
                current_branch = 'main'  # Default fallback
            
            # Push to remote
            push_cmd = ['git', 'push', 'origin', current_branch]
            if self._run_git_command(push_cmd) is None:
                logger.warning("Failed to push to remote repository")
                return False
            
            logger.info(f"Index files pushed to remote branch: {current_branch}")
            return True
            
        except Exception as e:
            logger.error(f"Error pushing to remote: {e}")
            return False
    
    def setup_index_branch(self) -> bool:
        """Set up a dedicated branch for index files (alternative approach)"""
        if not self.is_git_repo or not self.is_github_actions:
            return False
            
        try:
            # Configure Git
            if not self.configure_git():
                return False
            
            # Check if index branch exists
            branch_exists = self._run_git_command(['git', 'show-ref', '--verify', '--quiet', 'refs/heads/index-data'])
            
            if branch_exists is None:
                # Create index branch
                if self._run_git_command(['git', 'checkout', '--orphan', 'index-data']) is None:
                    return False
                
                # Remove all files from the new branch
                if self._run_git_command(['git', 'rm', '-rf', '.']) is None:
                    logger.warning("Failed to clean index branch, continuing...")
                
                logger.info("Created new index-data branch")
            else:
                # Switch to existing index branch
                if self._run_git_command(['git', 'checkout', 'index-data']) is None:
                    return False
                logger.info("Switched to existing index-data branch")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up index branch: {e}")
            return False
    
    def commit_to_index_branch(self, files: List[str]) -> bool:
        """Commit index files to dedicated index branch"""
        if not self.setup_index_branch():
            return False
            
        try:
            # Copy index files to branch
            existing_files = [f for f in files if os.path.exists(f)]
            if not existing_files:
                logger.warning("No index files found to commit")
                return False
            
            # Add files
            add_cmd = ['git', 'add'] + existing_files
            if self._run_git_command(add_cmd) is None:
                return False
            
            # Commit
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            commit_msg = f"Update OneDrive index - {timestamp}"
            
            if self._run_git_command(['git', 'commit', '-m', commit_msg]) is None:
                # No changes to commit
                logger.info("No changes to commit to index branch")
                return True
            
            # Push index branch
            if self._run_git_command(['git', 'push', 'origin', 'index-data']) is None:
                logger.warning("Failed to push index branch")
                return False
            
            logger.info("Index files committed to index-data branch")
            
            # Switch back to main branch
            self._run_git_command(['git', 'checkout', 'main'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error committing to index branch: {e}")
            return False
    
    def load_index_from_branch(self, files: List[str]) -> bool:
        """Load index files from dedicated index branch"""
        if not self.is_git_repo:
            return False
            
        try:
            # Check if index branch exists
            branch_exists = self._run_git_command(['git', 'show-ref', '--verify', '--quiet', 'refs/heads/index-data'])
            if branch_exists is None:
                logger.info("No index-data branch found")
                return False
            
            # Get files from index branch without switching to it
            for file in files:
                try:
                    # Get file content from index branch
                    content = self._run_git_command(['git', 'show', f'index-data:{file}'])
                    if content is not None:
                        with open(file, 'w') as f:
                            f.write(content)
                        logger.info(f"Loaded {file} from index-data branch")
                except Exception as e:
                    logger.warning(f"Could not load {file} from index branch: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading from index branch: {e}")
            return False

    def commit_feedback_files(self, files: List[str], commit_message: str) -> bool:
        """Commit feedback files to the main branch in real-time"""
        if not self.is_git_repo:
            logger.warning("Not in a Git repository, cannot commit feedback files")
            return False
            
        if not self.is_github_actions:
            logger.info("Not running in GitHub Actions, skipping feedback commit")
            return False
            
        try:
            # Check if files exist
            existing_files = [f for f in files if os.path.exists(f)]
            if not existing_files:
                logger.warning("No feedback files found to commit")
                return False
            
            # Configure Git
            if not self.configure_git():
                return False
            
            # Make sure we're on main branch
            current_branch = self._run_git_command(['git', 'branch', '--show-current'])
            if current_branch != 'main':
                if self._run_git_command(['git', 'checkout', 'main']) is None:
                    logger.error("Failed to switch to main branch")
                    return False
            
            # Add files (force add to bypass .gitignore)
            add_cmd = ['git', 'add', '-f'] + existing_files
            if self._run_git_command(add_cmd) is None:
                logger.error("Failed to add feedback files to Git")
                return False
            
            # Check if there are changes to commit
            status_output = self._run_git_command(['git', 'status', '--porcelain'])
            if not status_output:
                logger.info("No new feedback changes to commit")
                return True
            
            # Commit changes with detailed message
            commit_cmd = ['git', 'commit', '-m', commit_message]
            if self._run_git_command(commit_cmd) is None:
                logger.error("Failed to commit feedback files")
                return False
            
            logger.info(f"Feedback files committed: {', '.join(existing_files)}")
            
            # Push to remote immediately
            return self._push_to_remote()
            
        except Exception as e:
            logger.error(f"Error committing feedback files: {e}")
            return False

    def setup_feedback_branch(self) -> bool:
        """Set up a dedicated branch for feedback files (alternative approach)"""
        if not self.is_git_repo or not self.is_github_actions:
            return False
            
        try:
            # Configure Git
            if not self.configure_git():
                return False
            
            # Check if feedback branch exists
            branch_exists = self._run_git_command(['git', 'show-ref', '--verify', '--quiet', 'refs/heads/feedback-logs'])
            
            if branch_exists is None:
                # Create feedback branch from main
                if self._run_git_command(['git', 'checkout', '-b', 'feedback-logs']) is None:
                    return False
                logger.info("Created new feedback-logs branch")
            else:
                # Switch to existing feedback branch
                if self._run_git_command(['git', 'checkout', 'feedback-logs']) is None:
                    return False
                logger.info("Switched to existing feedback-logs branch")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up feedback branch: {e}")
            return False

    def commit_to_feedback_branch(self, files: List[str], commit_message: str) -> bool:
        """Commit feedback files to dedicated feedback branch"""
        if not self.setup_feedback_branch():
            return False
            
        try:
            # Add feedback files
            existing_files = [f for f in files if os.path.exists(f)]
            if not existing_files:
                logger.warning("No feedback files found to commit")
                return False
            
            # Add files (force add to bypass .gitignore)
            add_cmd = ['git', 'add', '-f'] + existing_files
            if self._run_git_command(add_cmd) is None:
                return False
            
            # Commit
            if self._run_git_command(['git', 'commit', '-m', commit_message]) is None:
                # No changes to commit
                logger.info("No changes to commit to feedback branch")
                return True
            
            # Push feedback branch
            if self._run_git_command(['git', 'push', 'origin', 'feedback-logs']) is None:
                logger.warning("Failed to push feedback branch")
                return False
            
            logger.info("Feedback files committed to feedback-logs branch")
            
            # Switch back to main branch
            self._run_git_command(['git', 'checkout', 'main'])
            
            return True
            
        except Exception as e:
            logger.error(f"Error committing to feedback branch: {e}")
            return False

    def load_feedback_from_branch(self, files: List[str]) -> bool:
        """Load feedback files from Git branch or main branch"""
        if not self.is_git_repo:
            return False
            
        try:
            # First try to get files from feedback-logs branch if it exists
            branch_exists = self._run_git_command(['git', 'show-ref', '--verify', '--quiet', 'refs/heads/feedback-logs'])
            
            if branch_exists is not None:
                # Try to load from feedback-logs branch
                for file in files:
                    try:
                        content = self._run_git_command(['git', 'show', f'feedback-logs:{file}'])
                        if content is not None:
                            with open(file, 'w') as f:
                                f.write(content)
                            logger.info(f"Loaded {file} from feedback-logs branch")
                    except Exception as e:
                        logger.warning(f"Could not load {file} from feedback-logs branch: {e}")
            else:
                # Try to load from main branch
                for file in files:
                    try:
                        content = self._run_git_command(['git', 'show', f'main:{file}'])
                        if content is not None:
                            with open(file, 'w') as f:
                                f.write(content)
                            logger.info(f"Loaded {file} from main branch")
                    except Exception as e:
                        logger.warning(f"Could not load {file} from main branch: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading feedback from branch: {e}")
            return False

# Global instance
git_manager = GitIndexManager()
