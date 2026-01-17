#!/usr/bin/env python3
"""
Secure startup script for FastAPI + Uvicorn with mutual TLS,
supporting TLS 1.2 and TLS 1.3 simultaneously.
"""
import ssl
import uvicorn
import os

# === Constants ===
APP = "main: app"
HOST = "127.0.0.1" # IP or domain name
PORT = 8000

#=== Restrict cipher suite ===
ALLOWED CIPHERS = (
  'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:'
  'DHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256'
)
LOG DIR = "./logs"
ACCESS_LOG = os.path.join(LOG_DIR, "access.log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")

SERVER CERT = "certs/proxy.crt"
SERVER KEY = "certs/proxy.key"
CLIENT_CA = "certs/client-ca.crt"

#=== Ensure log directory exists ===
os. makedirs(LOG_DIR, exist_ok=True)

#=== Start Uvicorn with SSL context ===
if __name__ == "__main__":
  print(f"Starting Uvicorn with mTLS on https://{HOST}: {PORT}")
  print("TLS 1.2 and 1.3 enabled; clients must present a valid certificate.")
  config = uvicorn.Config(
    APP,
    host=HOST,
    port=PORT,
    ssl_keyfile=SERVER_KEY,
    ssl_certfile=SERVER_CERT,
    ssl_ca_certs=CLIENT_CA,
    ss1_cert_reqs=ssl.CERT_REQUIRED,
    ssl_ciphers=ALLOWED_CIPHERS,
    log_level="info",
    access_log=True
  )
  
  server = uvicorn.Server(config)
  server.run()
