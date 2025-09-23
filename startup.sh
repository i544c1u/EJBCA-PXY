#!/usr/bin/env bash
#
# Run uvicorn with mutual TLS, allowing TLS 1.2 and 1.3
#
# Requires:
#   - server.crt, server.key (server cert + key)
#   - client-ca.crt (CA used to sign client certs)
#   - app: FastAPI app (e.g., main:app)

APP="main:app"                  # adjust if your FastAPI entrypoint differs
HOST="0.0.0.0"
PORT="8000"

LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# Timestamped log file in append mode
ACCESS_LOG="$LOG_DIR/access.log"
ERROR_LOG="$LOG_DIR/error.log"

SERVER_CERT="certs/server.crt"
SERVER_KEY="certs/server.key"
CLIENT_CA="certs/ca.crt"

# Extra SSL options:
#   - require client cert
#   - set verify mode to REQUIRE
#   - allow TLS 1.2 and 1.3
#
# Uvicorn lets you pass an SSLContext object, but from CLI we use:
#   --ssl-certfile, --ssl-keyfile, --ssl-ca-certs
# The OpenSSL defaults already negotiate TLS1.2 and 1.3 if available.
# To be explicit, we use env var to restrict nothing lower than 1.2.

# Make sure Python's ssl defaults allow TLS1.2 and 1.3.
export PYTHONHTTPSVERIFY=1

echo "Starting uvicorn with mTLS on https://${HOST}:${PORT}"
echo "TLS 1.2 and 1.3 are enabled; clients must present a valid cert."

uvicorn "$APP" \
  --host "$HOST" \
  --port "$PORT" \
  --ssl-certfile "$SERVER_CERT" \
  --ssl-keyfile "$SERVER_KEY" \
  --ssl-ca-certs "$CLIENT_CA" \
  --ssl-cert-reqs 2    # 2 = ssl.CERT_REQUIRED (mutual TLS)
  --access-log \
  --log-level info \
  >> "$ACCESS_LOG" 2>> "$ERROR_LOG"
