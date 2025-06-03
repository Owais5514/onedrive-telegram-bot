#!/usr/bin/env python3
"""
AI Model Server
Loads the AI model once and serves it via HTTP API
This prevents the bot from reloading the model each time
"""

import os
import json
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Model Server", version="1.0.0")

class QueryRequest(BaseModel):
    query: str
    context: str = ""
    max_length: int = 150

class ModelServer:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        self.loading = False
        
    async def load_model(self):
        """Load the AI model in background"""
        if self.loading or self.model_loaded:
            return
            
        self.loading = True
        logger.info("🔄 Loading AI model...")
        
        try:
            # Use a smaller, more efficient model for CodeSpace
            model_name = "microsoft/DialoGPT-small"  # Much smaller than Phi-1.5
            
            logger.info(f"Loading tokenizer for {model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            logger.info(f"Loading model {model_name}...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float32,  # Use float32 instead of auto
                device_map="cpu",  # Force CPU to avoid memory issues
                low_cpu_mem_usage=True
            )
            
            # Set padding token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.model_loaded = True
            logger.info("✅ AI model loaded successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error loading model: {e}")
            self.model = None
            self.tokenizer = None
        finally:
            self.loading = False
    
    def generate_response(self, query: str, context: str = "", max_length: int = 150) -> str:
        """Generate AI response"""
        if not self.model_loaded:
            return "AI model is not loaded yet. Please try again in a moment."
        
        try:
            # Prepare input
            if context:
                input_text = f"Context: {context[:500]}\nQuery: {query}\nResponse:"
            else:
                input_text = f"Query: {query}\nResponse:"
            
            # Tokenize
            inputs = self.tokenizer.encode(input_text, return_tensors="pt", max_length=512, truncation=True)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=min(inputs.shape[1] + max_length, 1024),
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=2
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the new part (after "Response:")
            if "Response:" in response:
                response = response.split("Response:")[-1].strip()
            
            return response[:max_length] if response else "I couldn't generate a response."
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error generating response: {str(e)}"

# Global model server instance
model_server = ModelServer()

@app.on_event("startup")
async def startup_event():
    """Start model loading on server startup"""
    asyncio.create_task(model_server.load_model())

@app.get("/")
async def root():
    return {"message": "AI Model Server", "model_loaded": model_server.model_loaded}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model_server.model_loaded,
        "loading": model_server.loading
    }

@app.post("/generate")
async def generate(request: QueryRequest):
    """Generate AI response"""
    if not model_server.model_loaded:
        if model_server.loading:
            raise HTTPException(status_code=503, detail="Model is still loading, please try again in a moment")
        else:
            raise HTTPException(status_code=500, detail="Model failed to load")
    
    try:
        response = model_server.generate_response(
            query=request.query,
            context=request.context,
            max_length=request.max_length
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🤖 Starting AI Model Server...")
    print("📍 Server will be available at http://localhost:8001")
    print("📚 API docs at http://localhost:8001/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    )
