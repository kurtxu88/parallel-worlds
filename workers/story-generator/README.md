# Story Generator Worker

The story generator worker polls Postgres for `pending` stories, claims one job at a time, generates the world graph, imports it into Neo4j, and marks the story as completed or failed.

## Run Locally

```bash
pip install -r requirements.txt
python worker.py
```
