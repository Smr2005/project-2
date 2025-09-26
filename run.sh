#!/usr/bin/env bash
# run.sh - start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
