# FleetScout Dashboard

## Run Locally (development)
```bash
uvicorn main:app --reload
```

## Render Start Command (production)
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Notes
- Use `--reload` only for local development.
- This project is FastAPI (`from fastapi import FastAPI` in `main.py`).
