# GBEDU Brain Engine

An AI producer that analyzes a vocal and generates a matching beat.

## Status
- Layer 1: Mock pipeline (working end-to-end)
- Layer 2: Real Essentia analysis (next)
- Layer 3: ACE-Step generation
- Layer 4: SongSpec Brain
- Layer 5: Memory
- Layer 6: Studio app integration

## Endpoints
- POST /v1/produce
- GET /v1/jobs/<job_id>
- GET /health

## Run
PYTHONPATH=src uv run python src/gbedu_brain/server.py
