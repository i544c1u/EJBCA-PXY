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
