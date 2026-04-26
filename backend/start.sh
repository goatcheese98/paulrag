#!/usr/bin/env bash
# Just start the API. Seeding is done once via the /api/admin/import-db endpoint.
exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-8000}"
