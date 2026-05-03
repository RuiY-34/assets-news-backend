#!/bin/bash
# Start the FastAPI backend (Groq cloud AI — no Ollama needed)
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
