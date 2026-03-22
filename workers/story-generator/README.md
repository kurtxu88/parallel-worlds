# Story Generator Worker

The story generator worker polls Postgres for `pending` stories, claims one job at a time, generates the world graph, imports it into Neo4j, and marks the story as completed or failed.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://parallel_worlds:parallel_worlds@localhost:5432/parallel_worlds
export NEO4J_URI=bolt://localhost:7687
python3 worker.py
```
