#!/usr/bin/env python3
"""
Database Manager for OneDrive Telegram Bot
Handles persistent storage using PostgreSQL on Render
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, BigInteger, String, Text, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database base
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    added_at = Column(DateTime, default=datetime.utcnow)

class Feedback(Base):
    __tablename__ = 'feedback'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    message = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)

class Cache(Base):
    __tablename__ = 'cache'
    
    key = Column(String(255), primary_key=True)
    value = Column(JSONB)
    updated_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self):
        """Initialize database connection"""
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            logger.warning("DATABASE_URL not found. Database operations will be disabled.")
            self.engine = None
            self.Session = None
            self.enabled = False
            return
        
        try:
            # Handle both postgres:// and postgresql:// URLs
            if self.database_url.startswith('postgres://'):
                self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
            
            self.engine = create_engine(self.database_url, echo=False)
            self.Session = sessionmaker(bind=self.engine)
            self.enabled = True
            logger.info("Database connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.engine = None
            self.Session = None
            self.enabled = False

    def create_tables(self):
        """Create all database tables"""
        if not self.enabled:
            return False
        
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created/verified successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            return False

    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Add a user to the database"""
        if not self.enabled:
            return False
        
        try:
            session = self.Session()
            # Check if user already exists
            existing_user = session.query(User).filter(User.user_id == user_id).first()
            if existing_user:
                # Update existing user info
                if username:
                    existing_user.username = username
                if first_name:
                    existing_user.first_name = first_name
                if last_name:
                    existing_user.last_name = last_name
            else:
                # Add new user
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
            
            session.commit()
            session.close()
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False

    def remove_user(self, user_id: int) -> bool:
        """Remove a user from the database"""
        if not self.enabled:
            return False
        
        try:
            session = self.Session()
            user = session.query(User).filter(User.user_id == user_id).first()
            if user:
                session.delete(user)
                session.commit()
            session.close()
            return True
        except Exception as e:
            logger.error(f"Error removing user {user_id}: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False

    def get_all_users(self) -> Set[int]:
        """Get all user IDs as a set"""
        if not self.enabled:
            return set()
        
        try:
            session = self.Session()
            users = session.query(User.user_id).all()
            session.close()
            return set(user[0] for user in users)
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            if 'session' in locals():
                session.close()
            return set()

    def get_user_count(self) -> int:
        """Get total number of users"""
        if not self.enabled:
            return 0
        
        try:
            session = self.Session()
            count = session.query(User).count()
            session.close()
            return count
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            if 'session' in locals():
                session.close()
            return 0

    def add_feedback(self, user_id: int, message: str) -> bool:
        """Add feedback to the database"""
        if not self.enabled:
            return False
        
        try:
            session = self.Session()
            feedback = Feedback(user_id=user_id, message=message)
            session.add(feedback)
            session.commit()
            session.close()
            logger.info(f"Feedback added for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding feedback: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False

    def get_recent_feedback(self, limit: int = 10) -> List[Dict]:
        """Get recent feedback entries"""
        if not self.enabled:
            return []
        
        try:
            session = self.Session()
            feedback_entries = session.query(Feedback).order_by(Feedback.submitted_at.desc()).limit(limit).all()
            
            results = []
            for entry in feedback_entries:
                results.append({
                    'id': entry.id,
                    'user_id': entry.user_id,
                    'message': entry.message,
                    'submitted_at': entry.submitted_at.isoformat()
                })
            
            session.close()
            return results
        except Exception as e:
            logger.error(f"Error fetching feedback: {e}")
            if 'session' in locals():
                session.close()
            return []

    def save_cache(self, key: str, value: dict) -> bool:
        """Save data to cache table"""
        if not self.enabled:
            return False
        
        try:
            session = self.Session()
            # Check if cache entry exists
            cache_entry = session.query(Cache).filter(Cache.key == key).first()
            if cache_entry:
                cache_entry.value = value
                cache_entry.updated_at = datetime.utcnow()
            else:
                cache_entry = Cache(key=key, value=value)
                session.add(cache_entry)
            
            session.commit()
            session.close()
            return True
        except Exception as e:
            logger.error(f"Error saving cache for key {key}: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False

    def get_cache(self, key: str) -> Optional[dict]:
        """Get data from cache table"""
        if not self.enabled:
            return None
        
        try:
            session = self.Session()
            cache_entry = session.query(Cache).filter(Cache.key == key).first()
            session.close()
            
            if cache_entry:
                return cache_entry.value
            return None
        except Exception as e:
            logger.error(f"Error fetching cache for key {key}: {e}")
            if 'session' in locals():
                session.close()
            return None

    def get_cache_timestamp(self, key: str) -> Optional[datetime]:
        """Get cache timestamp for a key"""
        if not self.enabled:
            return None
        
        try:
            session = self.Session()
            cache_entry = session.query(Cache).filter(Cache.key == key).first()
            session.close()
            
            if cache_entry:
                return cache_entry.updated_at
            return None
        except Exception as e:
            logger.error(f"Error fetching cache timestamp for key {key}: {e}")
            if 'session' in locals():
                session.close()
            return None

    def migrate_from_files(self, users_file: str = 'unlimited_users.json', feedback_file: str = 'feedback_log.txt') -> bool:
        """Migrate existing file-based data to database"""
        if not self.enabled:
            logger.warning("Database not enabled, cannot migrate data")
            return False
        
        success = True
        
        # Migrate users
        if os.path.exists(users_file):
            try:
                with open(users_file, 'r') as f:
                    user_ids = json.load(f)
                    
                for user_id in user_ids:
                    if not self.add_user(user_id):
                        success = False
                        
                logger.info(f"Migrated {len(user_ids)} users from {users_file}")
            except Exception as e:
                logger.error(f"Error migrating users from {users_file}: {e}")
                success = False
        
        # Migrate feedback (simple text format)
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        # Store as admin feedback since we don't have user context
                        self.add_feedback(0, f"Legacy feedback:\n{content}")
                        
                logger.info(f"Migrated feedback from {feedback_file}")
            except Exception as e:
                logger.error(f"Error migrating feedback from {feedback_file}: {e}")
                success = False
        
        return success

# Global database manager instance
db_manager = DatabaseManager()
