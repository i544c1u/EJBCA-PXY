### ✅ **Adapter (FastAPI + WebSockets)**

* Built a **FastAPI service** that:
  * Presents `server.crt`/`server.key` for inbound TLS.
  * Requires client certs and validates against `(client-)ca.crt`.
    (So client still performs mTLS to proxy.)
  * Accepts **RESTful JSON requests**.
  * Parse incoming REST JSON, translates them into **SOAP XML**.
  * Sends SOAP over a **WebSocket connection** to a mock SOAP server.
  * Receives SOAP normal responses (200|OK, 201|Created) and converts them back into **JSON** → send back to client over the original mTLS session.
  * Handles SOAP faults with proper error responses (HTTP 400 / 502 / 504).

* Implemented **REST endpoints** wrap 3 **EJBCA interfaces**:
  * `v1/endentity` End Entity REST Management API / request a certificate creation → wraps SOAP `editUser (UserDataVOWSuser)`
  
  e.g. 1
  ```json
  {
    "username": "JohnDoe",
    "password": "foo123",
    "subject_dn": "CN=John Doe,SURNAME=Doe,GIVENNAME=John,C=SE",
    "subject_alt_name": "rfc822Name=john.doe@example.com",
    "email": "john.doe@example.com",
    "extension_data": [
        {
            "name": "1.3.6.1.5.5.7.1.24/customdata_STARTTIME",
            "value": "3003020105/2022-12-13 00:00:00"
        }
    ],
    "custom_data": [
        {
            "name": "1.3.6.1.5.5.7.1.24/customdata_STARTTIME",
            "value": "3003020105/2022-12-13 00:00:00"
        }
    ],
    "ca_name": "ExampleCA",
    "certificate_profile_name": "ENDUSER",
    "end_entity_profile_name": "ExampleEEP",
    "token": "P12",
    "account_binding_id": "1234567890",
    "key_recoverable": false,
    "status": "NEW",
    "send_notification": false,
    "start_time": "ISO 8601 Date string, eg. '2023-06-15 14:07:09'",
    "end_time": "ISO 8601 Date string, eg. '2023-06-15 14:07:09'",
    "certificate_serial_number": 1234567890,
    "card_number": "1234567890"
  }
  ```
  e.g. 2
  ```json
  {
    "username": "devicename_2025-09-18T12:34:56.78901234Z",
    "email": "stardust.lu@lumi.com",
    "password": "password",
    "certificate_profile_name": "Lumi Client DEV - RSA 23mo",
    "end_entity_profile_name": "Lumi Client",
    "subject_dn": "L=Shanghai,ST=Shanghai,C=CN,O=Lumi,OU=Dev,CN=Stardust Lu,SURNAME=Lu,GIVENNAME=Stardust",
    "subject_alt_name":null,
    "ca_name": "e-commQASign",
    "extension_data": null,
    "key_recoverable": false,
    "custom_data": [
        {
          "name": "customdata_ENDTIME",
          "value": "2027-10-26 00:00:00"
        }
    ]
  }
  ```

  * `v1/certificate/certificaterequest` Enrollment with client generated keys for an existing End Entity / get certificate (requires the certificate to approved before it returns it) → wraps SOAP `certificateRequest`

  e.g.
  ```json
  {
    "certificate_request": "-----BEGIN CERTIFICATE REQUEST-----\nMIICh...V8shQ==\n-----END CERTIFICATE REQUEST-----",
    "username": "api-test",
    "password": "foo123",
    "include_chain": true,
    "certificate_authority_name": "Lumi Issuing CA",
    "certificate_request_type": "PUBLICKEY, PKCS10, CRMF, SPKAC, or CVC"
  }
  ```

  * `/v1/certificate/search` Searches for certificates confirming given criteria → wraps SOAP `findCerts(String username) or getCertificates(String username)`
  > note: SOAP API search func. allows `username`, `serial number`, or `subject DN` only.
  
  e.g.1
  ```json
  {
    "max_number_of_results": 10,
    "criteria": [
      {
        "property": "QUERY",
        "value": "02cc0d72edshaiuah728kk_2025-09-18T12:34:56.78901234Z",
        "operation": "EQUAL"
      }
    ]
  }
  ```

  e.g.2
  ```json
  {
    "criteria": [
      {
        "property": "CERTIFICATE_PROFILE",
        "value": "ENDUSER",
        "operation": "EQUAL"
      }
    ],
    "max_number_of_results": 10,
    "current_page": 0
  }
  ```
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
> Refer to: https://docs.keyfactor.com/ejbca/latest/open-api-specification
* REST → SOAP → REST flow validated with test commands:

```bash
# v1/certificate/certificaterequest
curl -X POST https://localhost:8000/v1/certificate/certificaterequest \
  -H "Content-Type: application/json" \
  -d '{
        "certificateRequest": "-----BEGIN CERTIFICATE REQUEST----------BEGIN CERTIFICATE REQUEST-----\nMIICvTCCAaUCAQAweDEPMA0GA1UEBwwGUHVkb25nMREwDwYDVQQIDAhTaGFuZ2hh\naTELMAkGA1UEBhMCQ04xETAPBgNVBAoMCFN0YXJkdXN0MREwDwYDVQQLDAhTdGFy\nZHVzdDEfMB0GA1UEAwwWYnRoZC0wOTE4LnN0YXJkdXN0LmNvbTCCASIwDQYJKoZI\nhvcNAQEBBQADggEPADCCAQoCggEBALOhVM0L7Olg7bY1HOEbf4mMC2YuqMKBleoA\nKarHCJkZI3qqKTNV7BYfzZaCXjPkFioE2WPQwMnkY0GmIXJZWSKlN0VOlJ6rod4X\n6IzDdw1HGdqnefyl6JbyM1RImgFe59Fw9Ebxpl0O1Eha178nz/Iw9W0XUQMqPx3c\nmh6pEy1+tTQaCWMsvtg+iHOtw06TVdQEa3nOHS0mPWaZCmna/MtdYnIOUmMWxvym\nBB5tgVzGAoOPcQ57mD3ZNU1ygILRpMpk6L0ZxDI6+eDDFEZBlfvmv0mO1r6KQdKd\nqMSP2MkR1wYsASEqJN1SafiXFeHCzQYr8xmbzvsGzkQoCB12nTcCAwEAAaAAMA0G\nCSqGSIb3DQEBCwUAA4IBAQBJBHLhFwsqlKquD+/WJztF9jhLJmVWIVUq4zmd/LyU\n+tAhtuIkFug53sPxQldV4CX0Vv2q+YfbHrDtRqnj7Y4eZwiJ23TkM3p0qMDgPoLo\nJavXC+W8H4UpK3hA01rhR9miUwZJXu74CEAhZtC1x8HwAF+O3NNZI5SJysNfLPxD\nPZXeBGXXQkA4kkW1ZrJqXRjXvV5a2rBL4WMiL5dqBq4XhQbrfAe4loTRm3TLT/Q3\nk3ioecnhFZkQ5ecB0Uc3PCKgOoc1nxjdl0aCbJBKrj8eSbnVoNBRHRbpVkIk2/I2\nUZlkbMy5XWrYwpyF8dIFbe2zxNf0mHvyTHt\n-----END CERTIFICATE REQUEST-----",
        "username": "jdoe",
        "password": "SecretPass123",
        "certificateProfile": "ENDUSER",
        "endEntityProfile": "EMPTY",
        "caName": "ManagementCA"
      }' \
     --cert certs/client.crt \
     --key certs/client.key \
     --cacert certs/ca.crt

curl -X POST https://localhost:8000/v1/certificate/certificaterequest \
  -H "Content-Type: application/json" \
  -d '{
        "certificateRequest": "-----BEGIN CERTIFICATE REQUEST----------BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----",
        "password": "SecretPass123",
        "certificateProfile": "ENDUSER",
        "endEntityProfile": "EMPTY",
        "caName": "ManagementCA"
      }' \
     --cert certs/client.crt \
     --key certs/client.key \
     --cacert certs/ca.crt

# v1/certificate/search
curl -X POST https://localhost:8000/v1/certificate/search \
  -H "Content-Type: application/json" \
  -d '{
        "query": {
            "username": "jdoe",
            "status": "ISSUED"
        },
        "page": 1,
        "pageSize": 25
      }' \
     --cert certs/client.crt \
     --key certs/client.key \
     --cacert certs/ca.crt

# v1/endentity
curl -X POST http://localhost:8000/v1/endentity \
  -H "Content-Type: application/json" \
  -d '{
        "username": "jdoe",
        "password": "SecretPass123",
        "commonName": "John Doe",
        "email": "john.doe@example.org",
        "endEntityProfile": "EMPTY",
        "certificateProfile": "ENDUSER",
        "caName": "ManagementCA"
      }' \
     --cert certs/client.crt \
     --key certs/client.key \
     --cacert certs/ca.crt
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
