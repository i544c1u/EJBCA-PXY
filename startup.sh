#!/bin/bash
# Start FastAPI Adapter with mTLS and audit logging

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# Timestamped log file in append mode
ACCESS_LOG="$LOG_DIR/access.log"
ERROR_LOG="$LOG_DIR/error.log"

# Run uvicorn with:
# - 4 worker processes
# - mTLS enabled
# - audit-friendly logging
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port 8666 \
  --workers 4 \
  --ssl-keyfile=./server.key \
  --ssl-certfile=./server.crt \
  --ssl-ca-certs=./ca.crt \
  --ssl-cert-reqs=2 \
  --access-log \
  --log-level info \
  >> "$ACCESS_LOG" 2>> "$ERROR_LOG"
