"""
AI Handler Client - Connects to Model Server
Lightweight version that uses HTTP API instead of loading models locally
"""

import json
import logging
import re
import asyncio
import httpx
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
import os

logger = logging.getLogger(__name__)

class AIHandlerClient:
    """AI Handler that connects to external model server"""
    
    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url
        self.file_index = {}
        self.file_paths = []
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Load file index for context-aware search
        self._load_file_index()
        
        logger.info(f"AI Handler Client initialized - connecting to {server_url}")
    
    def _load_file_index(self):
        """Load the file index for context-aware search"""
        try:
            index_path = 'file_index.json'
            if os.path.exists(index_path):
                with open(index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Handle different index formats
                if isinstance(data, list):
                    # List format - each item is a file/folder entry
                    sections = []
                    for item in data:
                        if isinstance(item, dict) and 'path' in item:
                            self.file_paths.append(item['path'])
                            
                            # Create searchable sections
                            sections.append({
                                'path': item['path'],
                                'content': f"{item['path']} {item.get('name', '')} {item.get('type', '')}"
                            })
                            
                    self.file_index = {'sections': sections}
                    logger.info(f"File index loaded with {len(sections)} sections")
                    
                elif isinstance(data, dict) and 'sections' in data:
                    # Already in the right format
                    self.file_index = data
                    self.file_paths = [s.get('path', '') for s in data['sections'] if s.get('path')]
                    logger.info(f"File index loaded with {len(data['sections'])} sections")
                    
                elif isinstance(data, dict):
                    # Directory structure format - keys are folder paths, values contain file info
                    sections = []
                    for folder_path, folder_data in data.items():
                        self.file_paths.append(folder_path)
                        
                        # Create searchable section for each folder
                        content = folder_path
                        if isinstance(folder_data, dict):
                            # Add file information if available
                            if 'files' in folder_data:
                                for file_info in folder_data['files']:
                                    if isinstance(file_info, dict) and 'name' in file_info:
                                        content += f" {file_info['name']}"
                                        if 'path' in file_info:
                                            self.file_paths.append(file_info['path'])
                        
                        sections.append({
                            'path': folder_path,
                            'content': content
                        })
                    
                    self.file_index = {'sections': sections}
                    logger.info(f"File index loaded with {len(sections)} sections from directory structure")
                    
                else:
                    logger.warning(f"Unexpected index format: {type(data)}")
                    self.file_index = {'sections': []}
                    
            else:
                logger.warning("File index not found, context-aware search disabled")
                self.file_index = {'sections': []}
                
        except Exception as e:
            logger.error(f"Error loading file index: {e}")
            self.file_index = {'sections': []}
    
    async def is_server_ready(self) -> bool:
        """Check if model server is ready"""
        try:
            response = await self.client.get(f"{self.server_url}/health")
            if response.status_code == 200:
                data = response.json()
                return data.get('model_loaded', False)
            return False
        except Exception as e:
            logger.error(f"Error checking server health: {e}")
            return False
    
    async def generate_response(self, query: str, context: str = "") -> str:
        """Generate AI response using model server"""
        try:
            # Check if server is ready
            if not await self.is_server_ready():
                return "🤖 AI model is starting up, please try again in a moment..."
            
            # Prepare request
            request_data = {
                "query": query,
                "context": context,
                "max_length": 150
            }
            
            # Call model server
            response = await self.client.post(
                f"{self.server_url}/generate",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'No response generated')
            elif response.status_code == 503:
                return "🤖 AI model is still loading, please try again in a moment..."
            else:
                logger.error(f"Server error: {response.status_code} - {response.text}")
                return "❌ Error generating AI response"
                
        except Exception as e:
            logger.error(f"Error calling model server: {e}")
            return "❌ AI service temporarily unavailable"
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            asyncio.create_task(self.client.aclose())
        except:
            pass
    
    # Keep all the existing search methods from the original AI handler
    def extract_context_keywords(self, query: str, file_paths: List[str]) -> List[str]:
        """Extract context-aware keywords based on file paths and content"""
        keywords = []
        query_lower = query.lower()
        
        # Extract explicit keywords from query
        words = re.findall(r'\b\w+\b', query_lower)
        keywords.extend([w for w in words if len(w) > 2])
        
        # File type associations
        file_type_keywords = {
            'document': ['doc', 'docx', 'pdf', 'txt', 'document', 'file', 'text'],
            'spreadsheet': ['xls', 'xlsx', 'csv', 'sheet', 'excel', 'data'],
            'presentation': ['ppt', 'pptx', 'slide', 'presentation'],
            'image': ['jpg', 'jpeg', 'png', 'gif', 'image', 'photo', 'picture'],
            'video': ['mp4', 'avi', 'mkv', 'video', 'movie', 'film'],
            'audio': ['mp3', 'wav', 'music', 'audio', 'sound'],
            'code': ['py', 'js', 'html', 'css', 'code', 'script', 'program'],
            'archive': ['zip', 'rar', '7z', 'archive', 'compressed']
        }
        
        # Add file type keywords based on query intent
        for file_type, type_keywords in file_type_keywords.items():
            if any(keyword in query_lower for keyword in type_keywords):
                keywords.extend(type_keywords)
        
        # Temporal keywords
        temporal_keywords = {
            'recent': ['recent', 'new', 'latest', 'today', 'yesterday'],
            'old': ['old', 'previous', 'archive', 'backup'],
            'work': ['work', 'project', 'task', 'job', 'business'],
            'personal': ['personal', 'private', 'family', 'home']
        }
        
        for category, temp_keywords in temporal_keywords.items():
            if any(keyword in query_lower for keyword in temp_keywords):
                keywords.extend(temp_keywords)
        
        return list(set(keywords))
    
    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform semantic search using simple text matching"""
        if not self.file_index.get('sections'):
            return []
        
        query_lower = query.lower()
        results = []
        
        for section in self.file_index['sections']:
            content = section.get('content', '').lower()
            path = section.get('path', '')
            
            # Calculate relevance score
            score = 0.0
            
            # Exact phrase matching
            if query_lower in content:
                score += 1.0
            
            # Word matching
            query_words = set(re.findall(r'\b\w+\b', query_lower))
            content_words = set(re.findall(r'\b\w+\b', content))
            common_words = query_words.intersection(content_words)
            
            if query_words:
                word_score = len(common_words) / len(query_words)
                score += word_score * 0.8
            
            # Path relevance
            path_lower = path.lower()
            for word in query_words:
                if word in path_lower:
                    score += 0.3
            
            if score > 0:
                results.append({
                    'path': path,
                    'content': section.get('content', ''),
                    'score': score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def keyword_search(self, keywords: List[str], file_paths: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Perform keyword-based search"""
        results = []
        keywords_lower = [k.lower() for k in keywords]
        
        for path in file_paths:
            path_lower = path.lower()
            score = 0.0
            
            for keyword in keywords_lower:
                if keyword in path_lower:
                    # Exact match in filename gets higher score
                    filename = os.path.basename(path_lower)
                    if keyword in filename:
                        score += 2.0
                    else:
                        score += 1.0
            
            if score > 0:
                results.append({
                    'path': path,
                    'score': score,
                    'type': 'keyword_match'
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def fuzzy_search(self, query: str, file_paths: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Perform fuzzy string matching"""
        results = []
        query_lower = query.lower()
        
        for path in file_paths:
            filename = os.path.basename(path).lower()
            
            # Calculate similarity
            similarity = SequenceMatcher(None, query_lower, filename).ratio()
            
            # Also check against full path
            path_similarity = SequenceMatcher(None, query_lower, path.lower()).ratio()
            max_similarity = max(similarity, path_similarity)
            
            if max_similarity > 0.3:  # Threshold for fuzzy matching
                results.append({
                    'path': path,
                    'score': max_similarity,
                    'type': 'fuzzy_match'
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def recommend_folders(self, query: str, file_paths: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Recommend relevant folders based on query"""
        folders = set()
        query_lower = query.lower()
        
        # Extract unique directories
        for path in file_paths:
            dir_path = os.path.dirname(path)
            if dir_path and dir_path not in folders:
                folders.add(dir_path)
        
        folder_results = []
        
        for folder in folders:
            folder_lower = folder.lower()
            score = 0.0
            
            # Check if query words appear in folder path
            query_words = re.findall(r'\b\w+\b', query_lower)
            for word in query_words:
                if word in folder_lower:
                    score += 1.0
            
            # Boost score for folders that contain many matching files
            matching_files = [p for p in file_paths if p.startswith(folder)]
            if matching_files:
                score += len(matching_files) * 0.1
            
            if score > 0:
                folder_results.append({
                    'path': folder,
                    'score': score,
                    'type': 'folder',
                    'file_count': len(matching_files)
                })
        
        folder_results.sort(key=lambda x: x['score'], reverse=True)
        return folder_results[:limit]
    
    async def enhanced_search(self, query: str, file_paths: List[str]) -> Tuple[str, List[Dict[str, Any]]]:
        """Enhanced search with multiple strategies"""
        # Extract context-aware keywords
        keywords = self.extract_context_keywords(query, file_paths)
        
        # Perform multiple search strategies
        semantic_results = self.semantic_search(query, limit=5)
        keyword_results = self.keyword_search(keywords, file_paths, limit=5)
        fuzzy_results = self.fuzzy_search(query, file_paths, limit=3)
        folder_results = self.recommend_folders(query, file_paths, limit=3)
        
        # Combine and deduplicate results
        all_results = []
        seen_paths = set()
        
        # Add semantic results first (highest priority)
        for result in semantic_results:
            if result['path'] not in seen_paths:
                result['source'] = 'semantic'
                all_results.append(result)
                seen_paths.add(result['path'])
        
        # Add keyword results
        for result in keyword_results:
            if result['path'] not in seen_paths:
                result['source'] = 'keyword'
                all_results.append(result)
                seen_paths.add(result['path'])
        
        # Add fuzzy results
        for result in fuzzy_results:
            if result['path'] not in seen_paths:
                result['source'] = 'fuzzy'
                all_results.append(result)
                seen_paths.add(result['path'])
        
        # Create context for AI response
        context_files = [r['path'] for r in all_results[:5]]
        context = f"Found files: {', '.join(context_files)}" if context_files else ""
        
        # Generate AI response with context
        try:
            ai_response = await self.generate_response(query, context)
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            ai_response = "I found some relevant files for your query."
        
        # Combine file and folder results
        combined_results = all_results + folder_results
        
        return ai_response, combined_results
