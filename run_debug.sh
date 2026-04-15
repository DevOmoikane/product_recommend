#!/bin/sh
uvicorn --host 0.0.0.0 --port 8000 --reload --log-level debug back_end.api.main:app
