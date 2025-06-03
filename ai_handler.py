#!/usr/bin/env python3
"""
AI Handler for OneDrive Telegram Bot
Handles AI-powered search using local Phi model
"""

import os
import re
import logging
from typing import List, Dict, Optional, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Configure logging
logger = logging.getLogger(__name__)

class AIHandler:
    def __init__(self):
        """Initialize AI handler with local Phi model"""
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        self.model_loading = False  # Flag to track if model is currently loading
        
        # Course code patterns (based on file_name_structure.md)
        self.course_patterns = [
            r'[A-Z]{2,4}\d{4}',  # CE1201, EEE2203, MATH1103 etc
            r'[A-Z]{3}\d{3}',    # MAT101, PHY201 etc
            r'[A-Z]{4}\d{3}',    # COMP101 etc
        ]
        
        # Common file type indicators
        self.file_type_mapping = {
            'lecture': ['L', 'LEC', 'LECTURE'],
            'quiz': ['Q', 'QUIZ'],
            'assignment': ['A', 'ASS', 'ASSIGNMENT', 'HW', 'HOMEWORK'],
            'exam': ['E', 'EXAM', 'TEST', 'MIDTERM', 'FINAL'],
            'lab': ['LAB', 'PRACTICAL'],
            'tutorial': ['T', 'TUT', 'TUTORIAL'],
            'project': ['P', 'PROJ', 'PROJECT'],
            'notes': ['N', 'NOTE', 'NOTES'],
            'solution': ['SOL', 'SOLUTION', 'ANS', 'ANSWER']
        }
        
    def load_model(self) -> bool:
        """Check if model is loaded (non-blocking)"""
        return self.model_loaded
    
    def is_model_ready(self) -> bool:
        """Check if model is ready for use"""
        return self.model_loaded and self.model is not None
    
    def is_loading(self) -> bool:
        """Check if model is currently loading"""
        return self.model_loading
    
    async def load_model_async(self) -> bool:
        """Load Phi model asynchronously in background"""
        if self.model_loaded or self.model_loading:
            return self.model_loaded
            
        self.model_loading = True
        
        try:
            logger.info("Starting background loading of Phi-1.5 model...")
            
            # Use Microsoft's Phi-1_5 model (smaller and faster)
            model_name = "microsoft/phi-1_5"
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=True
            )
            
            # Add pad token if it doesn't exist
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with optimizations for speed
            logger.info("Loading model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            # Set to evaluation mode
            self.model.eval()
            
            self.model_loaded = True
            self.model_loading = False
            logger.info("✅ Phi model loaded successfully and ready for AI search!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load Phi model: {e}")
            self.model_loading = False
            return False
    
    def start_background_loading(self):
        """Start loading model in background thread"""
        import threading
        import asyncio
        
        def load_in_thread():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.load_model_async())
                loop.close()
            except Exception as e:
                logger.error(f"Error in background model loading: {e}")
        
        # Start loading in background thread
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
        logger.info("🔄 AI model loading started in background...")

    def extract_course_codes(self, text: str) -> List[str]:
        """Extract course codes from text using regex patterns"""
        course_codes = []
        text_upper = text.upper()
        
        for pattern in self.course_patterns:
            matches = re.findall(pattern, text_upper)
            course_codes.extend(matches)
        
        return list(set(course_codes))  # Remove duplicates
    
    def identify_file_types(self, text: str) -> List[str]:
        """Identify file types from user query"""
        text_lower = text.lower()
        identified_types = []
        
        for file_type, keywords in self.file_type_mapping.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    identified_types.append(file_type)
                    break
        
        return list(set(identified_types))
    
    def generate_ai_keywords(self, user_query: str) -> List[str]:
        """Generate search keywords using AI model"""
        if not self.is_model_ready():
            if self.is_loading():
                logger.info("AI model still loading, using fallback keyword extraction")
            else:
                logger.warning("AI model not available, using fallback keyword extraction")
            return self.fallback_keyword_extraction(user_query)
        
        try:
            # Create a prompt for keyword extraction
            prompt = f"""Based on this university file search query, extract the most important search keywords.
Query: "{user_query}"

File naming context:
- Course codes follow patterns like CE1201, EEE2203, MATH1103
- Files have indicators like L01 (lecture 1), Q2 (quiz 2), A3 (assignment 3)
- Common types: lectures, quizzes, assignments, exams, labs, tutorials

Extract 3-5 key search terms:"""

            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=50,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
            
            # Extract keywords from response
            keywords = self.parse_ai_response(response, user_query)
            
            logger.info(f"AI generated keywords: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"Error generating AI keywords: {e}")
            return self.fallback_keyword_extraction(user_query)
    
    def parse_ai_response(self, response: str, original_query: str) -> List[str]:
        """Parse AI response to extract clean keywords"""
        keywords = []
        
        # Split response into lines and words
        words = response.replace('\n', ' ').split()
        
        # Filter and clean keywords
        for word in words:
            word = re.sub(r'[^\w\d]', '', word).strip()
            if len(word) > 2 and word.lower() not in ['the', 'and', 'for', 'are', 'with']:
                keywords.append(word)
        
        # Add course codes and file types from original query
        keywords.extend(self.extract_course_codes(original_query))
        keywords.extend(self.identify_file_types(original_query))
        
        # Remove duplicates and limit to 8 keywords
        return list(set(keywords))[:8]
    
    def fallback_keyword_extraction(self, user_query: str) -> List[str]:
        """Fallback keyword extraction without AI model"""
        keywords = []
        
        # Extract course codes
        keywords.extend(self.extract_course_codes(user_query))
        
        # Extract file types
        keywords.extend(self.identify_file_types(user_query))
        
        # Extract other meaningful words
        words = re.findall(r'\b\w{3,}\b', user_query.lower())
        stop_words = {'the', 'and', 'for', 'are', 'with', 'from', 'find', 'search', 'get', 'show', 'need', 'want'}
        
        for word in words:
            if word not in stop_words and len(word) > 2:
                keywords.append(word)
        
        return list(set(keywords))[:8]
    
    def process_ai_search(self, user_query: str) -> Tuple[List[str], str]:
        """
        Process AI search query and return keywords + explanation
        Returns: (keywords_list, explanation_text)
        """
        try:
            # Check model status
            model_status = ""
            if self.is_model_ready():
                model_status = "🤖 AI Model: Ready\n"
            elif self.is_loading():
                model_status = "🔄 AI Model: Loading (using fallback)\n"
            else:
                model_status = "⚠️ AI Model: Not available (using fallback)\n"
            
            # Generate keywords using AI or fallback
            keywords = self.generate_ai_keywords(user_query)
            
            # Create explanation
            explanation = f"🤖 AI Analysis:\n"
            explanation += model_status
            explanation += f"Query: \"{user_query}\"\n\n"
            explanation += f"🔍 Generated search keywords:\n"
            
            if keywords:
                for i, keyword in enumerate(keywords, 1):
                    explanation += f"{i}. {keyword}\n"
            else:
                explanation += "No specific keywords identified"
            
            return keywords, explanation
            
        except Exception as e:
            logger.error(f"Error processing AI search: {e}")
            fallback_keywords = self.fallback_keyword_extraction(user_query)
            explanation = f"⚠️ AI processing failed, using fallback keywords:\n"
            explanation += f"Keywords: {', '.join(fallback_keywords) if fallback_keywords else 'None'}"
            
            return fallback_keywords, explanation
    
    def cleanup(self):
        """Clean up model resources"""
        if self.model_loaded:
            try:
                del self.model
                del self.tokenizer
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                self.model_loaded = False
                logger.info("AI model resources cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up AI resources: {e}")
