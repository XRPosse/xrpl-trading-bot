# Python Setup Guide

## Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
src/
├── __init__.py
├── main.py      # Entry point
├── models/      # Data models
├── services/    # Business logic
└── utils/       # Helper functions
```

## Common Dependencies

```txt
# requirements.txt
fastapi          # Web framework
uvicorn         # ASGI server
pytest          # Testing
black           # Code formatter
```

## Running the App

```bash
# Development
uvicorn src.main:app --reload

# Production
uvicorn src.main:app --host 0.0.0.0
```

---
Last updated: [Date]