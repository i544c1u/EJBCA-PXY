### ✅ **Adapter (FastAPI + WebSockets)**

* Built a **FastAPI service** that:
  * Presents `server.crt`/`server.key` for inbound TLS.
  * Requires client certs and validates against `ca.crt`.
    (So client still performs mTLS to proxy.)
  * Accepts **RESTful JSON requests**.
  * Parse incoming REST JSON, translates them into **SOAP XML**.
  * Sends SOAP over a **WebSocket connection** to a mock SOAP server.
  * Receives SOAP responses and converts them back into **JSON** → send back to client over the original mTLS session.
  * Handles SOAP faults with proper error responses (HTTP 400 / 502 / 504).

* Implemented **endpoints**:
  * `/recover_key` → wraps SOAP `RecoverKeyRequest`
  * `/key_recovery_enroll` → wraps SOAP `KeyRecoveryEnrollRequest`
  * `/cert_query/{query_type}` → generic wrapper for certificate query functions
  * `/soap-to-json` → raw SOAP → JSON parser
  * `/health` → simple health check

* Wrap 2 more EJBCA **REST interfaces** (todo):
  * `v1/certificate` Certificate REST Management API
  * `v1/endentity` End Entity REST Management API
  > https://docs.keyfactor.com/ejbca/latest/open-api-specification

* Security controls
  * Store outbound cert/key in an HSM or secure keystore (never plaintext).
  * Limit filesystem ACLs to proxy service account.
  * Use ephemeral client certs for proxy-to-server (rotate frequently).
  * Keep separate certs: do **not** reuse end-user certs for proxy unless unavoidable.

* Audit & monitoring
  * Log: request timestamp, client cert fingerprint, client cert serial, request path, SOAP endpoint called, outcome (success/fault), response code. Append-mode logs.
  * Log file integrity: send to remote central log collector or SIEM (immutable storage).
  * Alert on use of expired cert, abnormal request volume per client cert, or unexpected cert fingerprint changes.

* Rotation & lifecycle
  * Automate rotation of proxy outbound certs; maintain overlap period to avoid downtime.
  * Keep a revocation workflow: if a key leaks, immediately revoke and redeploy new key and cert.
---

### ✅ **Mock SOAP Server (async websockets)**

* Mock server listens on `ws://localhost:8888`.

* Handles multiple request types with simulated responses:

  * **Key Recovery** (`RecoverKeyRequest`) → returns recovered key.
  * **Key Recovery Enroll** (`KeyRecoveryEnrollRequest`) → returns enrollment confirmation.
  * **Certificate Queries**:

    * `FindCertsRequest` → returns multiple certs.
    * `GetCertificateRequest` → returns a single certificate.
    * `GetLastCAChainRequest` → returns a CA chain.
  * **Error case** → if message contains `<username>error</username>` or `<serialNumber>error</serialNumber>`, returns a SOAP fault.
  * **Fallback** → generic response for unknown requests.

* Includes **developer-friendly `print()` logging** of requests and responses.

---

### ✅ **Test Cases (curl examples)**

* REST → SOAP → REST flow validated with test commands:

  ```bash
  # Recover key
  curl -X POST http://localhost:8666/recover_key \
       -H "Content-Type: application/json" \
       -d '{"serialNumber":"12345","username":"alice"}'

  # Key recovery enrollment
  curl -X POST http://localhost:8666/key_recovery_enroll \
       -H "Content-Type: application/json" \
       -d '{"serialNumber":"12345","username":"alice","enrollmentCode":"xyz"}'

  # Certificate queries
  curl -X POST http://localhost:8666/cert_query/FindCertsRequest
  curl -X POST http://localhost:8666/cert_query/GetCertificateRequest
  curl -X POST http://localhost:8666/cert_query/GetLastCAChainRequest
  ```

---

👉 Hence, we have a working **SOAP–REST adapter prototype** with mock backend coverage for:

* **Key Recovery**
* **Key Recovery Enroll**
* **Certificate Query suite**
* **Error handling**

---

### ✅ Correct way for testing mTLS

If you just want to mock/test locally, you can create a full chain with **OpenSSL**:

1. **Create a test CA**:

   ```bash
   openssl genrsa -out ca.key 2048
   openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 \
       -out ca.crt -subj "/CN=MockTestCA"
   ```

2. **Create server cert signed by CA**:

   ```bash
   openssl genrsa -out server.key 2048
   openssl req -new -key server.key -out server.csr -subj "/CN=localhost"
   openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
       -out server.crt -days 365 -sha256
   ```

3. **Create client cert signed by CA**:

   ```bash
   openssl genrsa -out client.key 2048
   openssl req -new -key client.key -out client.csr -subj "/CN=testclient"
   openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
       -out client.crt -days 365 -sha256
   ```

4. **Run uvicorn with mTLS**:

   ```bash
   uvicorn main:app \
     --ssl-keyfile=./server.key \
     --ssl-certfile=./server.crt \
     --ssl-ca-certs=./ca.crt \
     --ssl-cert-reqs=2
   ```

5. **Test with curl using client cert**:

   ```bash
   curl -k https://localhost:8666/health \
     --cert client.crt --key client.key
   ```

👉 Generating a real `ca.crt` = proper testable mTLS where your REST adapter can act like a **Registration Authority (RA)**.

---

1. Make sure you have a CA cert file, e.g.:

   * `ca.crt` (public cert of the CA that issued your client certs)
   * `server.crt` (server public cert)
   * `server.key` (server private key)

2. Start uvicorn like this:

   ```bash
   uvicorn main:app \
     --host 0.0.0.0 --port 8666 \
     --ssl-keyfile=./server.key \
     --ssl-certfile=./server.crt \
     --ssl-ca-certs=./ca.crt \
     --ssl-cert-reqs=2
   ```

   ⚠️ Note the `./` → this forces uvicorn to look in the current directory.

3. If you don’t actually need to validate client certs yet (just TLS for now), you can skip the `--ssl-ca-certs` and `--ssl-cert-reqs` flags:

   ```bash
   uvicorn main:app --ssl-keyfile=./server.key --ssl-certfile=./server.crt
   ```

---

### 🔑 The original test (no TLS):

```bash
curl -X POST http://localhost:8666/key_recovery_enroll \
     -H "Content-Type: application/json" \
     -d '{"serialNumber":"12345","username":"alice","enrollmentCode":"xyz"}'
```

---

### 🔑 The mTLS version:

```bash
curl -k https://localhost:8666/key_recovery_enroll \
     --cert client.crt \
     --key client.key \
     -H "Content-Type: application/json" \
     -d '{"serialNumber":"12345","username":"alice","enrollmentCode":"xyz"}'
```

---

### Explanation

* `https://` → must switch to TLS.
* `-k` → skips strict hostname verification (okay for local testing).
* `--cert client.crt` → client’s certificate (signed by your mock CA).
* `--key client.key` → private key for that client cert.
* The rest (`-H`, `-d`) remains the same.

If you also need to specify the CA for verifying the **server’s cert** (instead of `-k`), you can use:

```bash
curl https://localhost:8666/key_recovery_enroll \
     --cert client.crt \
     --key client.key \
     --cacert ca.crt \
     -H "Content-Type: application/json" \
     -d '{"serialNumber":"12345","username":"alice","enrollmentCode":"xyz"}'
```

---

⚡ Tip: Once you enable mTLS, the adapter can **extract the client certificate serial number** and use it automatically in the SOAP call, so you don’t even need to pass `"serialNumber": "12345"` in the JSON anymore.
