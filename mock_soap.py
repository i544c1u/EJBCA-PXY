"""
> Refer to: https://docs.keyfactor.com/ejbca/latest/open-api-specification
# Recover key
curl -X POST https://localhost:8666/recover_key \
     -H "Content-Type: application/json" \
     -d '{"serialNumber":"12345","username":"alice"}'

# Key recovery enrollment
curl -X POST https://localhost:8666/key_recovery_enroll \
     -H "Content-Type: application/json" \
     -d '{"serialNumber":"12345","username":"alice","enrollmentCode":"xyz"}'

curl -X POST "https://localhost:8666/soap-to-json" -H "Content-Type: text/xml" --data-binary @sample_request.xml

# Certificate queries
curl -X POST https://localhost:8666/cert_query/FindCertsRequest
curl -X POST https://localhost:8666/cert_query/GetCertificateRequest
curl -X POST https://localhost:8666/cert_query/GetLastCAChainRequest

# v1/certificate/certificaterequest
curl -X POST https://localhost:8666/v1/certificate/certificaterequest \
  -H "Content-Type: application/json" \
  -d '{
        "certificateRequest": "-----BEGIN CERTIFICATE REQUEST----------BEGIN CERTIFICATE REQUEST-----\nMIICvTCCAaUCAQAweDEPMA0GA1UEBwwGUHVkb25nMREwDwYDVQQIDAhTaGFuZ2hh\naTELMAkGA1UEBhMCQ04xETAPBgNVBAoMCFN0YXJkdXN0MREwDwYDVQQLDAhTdGFy\nZHVzdDEfMB0GA1UEAwwWYnRoZC0wOTE4LnN0YXJkdXN0LmNvbTCCASIwDQYJKoZI\nhvcNAQEBBQADggEPADCCAQoCggEBALOhVM0L7Olg7bY1HOEbf4mMC2YuqMKBleoA\nKarHCJkZI3qqKTNV7BYfzZaCXjPkFioE2WPQwMnkY0GmIXJZWSKlN0VOlJ6rod4X\n6IzDdw1HGdqnefyl6JbyM1RImgFe59Fw9Ebxpl0O1Eha178nz/Iw9W0XUQMqPx3c\nmh6pEy1+tTQaCWMsvtg+iHOtw06TVdQEa3nOHS0mPWaZCmna/MtdYnIOUmMWxvym\nBB5tgVzGAoOPcQ57mD3ZNU1ygILRpMpk6L0ZxDI6+eDDFEZBlfvmv0mO1r6KQdKd\nqMSP2MkR1wYsASEqJN1SafiXFeHCzQYr8xmbzvsGzkQoCB12nTcCAwEAAaAAMA0G\nCSqGSIb3DQEBCwUAA4IBAQBJBHLhFwsqlKquD+/WJztF9jhLJmVWIVUq4zmd/LyU\n+tAhtuIkFug53sPxQldV4CX0Vv2q+YfbHrDtRqnj7Y4eZwiJ23TkM3p0qMDgPoLo\nJavXC+W8H4UpK3hA01rhR9miUwZJXu74CEAhZtC1x8HwAF+O3NNZI5SJysNfLPxD\nPZXeBGXXQkA4kkW1ZrJqXRjXvV5a2rBL4WMiL5dqBq4XhQbrfAe4loTRm3TLT/Q3\nk3ioecnhFZkQ5ecB0Uc3PCKgOoc1nxjdl0aCbJBKrj8eSbnVoNBRHRbpVkIk2/I2\nUZlkbMy5XWrYwpyF8dIFbe2zxNf0mHvyTHt\n-----END CERTIFICATE REQUEST-----",
        "username": "jdoe",
        "password": "SecretPass123",
        "certificateProfile": "ENDUSER",
        "endEntityProfile": "EMPTY",
        "caName": "ManagementCA"
      }'

# v1/certificate/search
curl -X POST https://localhost:8666/v1/certificate/search \
  -H "Content-Type: application/json" \
  -d '{
        "query": {
            "username": "jdoe",
            "status": "ISSUED"
        },
        "page": 1,
        "pageSize": 25
      }'

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
      }'
---
     --cert client.crt \
     --key client.key \
     --cacert ca.crt
"""

# File: mock_soap.py
import asyncio
import ssl
import websockets

HOST = 'localhost'
PORT = 8888

CERT_PATH = 'certs/server.crt'
KEY_PATH = 'certs/server.key'
CA_PATH = 'certs/ca.crt'

async def handle(ws):
    try:
        async for message in ws:
            print('\n--- Mock SOAP Server received ---')
            print(message)

            # Error case
            if '<username>error</username>' in message or '<serialNumber>error</serialNumber>' in message:
                fault = '''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <soap:Fault>
      <faultcode>soap:Client</faultcode>
      <faultstring>Simulated error for testing</faultstring>
    </soap:Fault>
  </soap:Body>
</soap:Envelope>'''
                print('\n--- Mock SOAP Server sending FAULT ---')
                print(fault)
                await ws.send(fault)
                continue

            # Key Recovery
            if 'RecoverKeyRequest' in message or 'KeyRecoveryEnrollRequest' in message:
                serial = 'unknown'
                if '<serialNumber>' in message:
                    start = message.find('<serialNumber>') + len('<serialNumber>')
                    end = message.find('</serialNumber>', start)
                    serial = message[start:end]
                resp = f'''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <RecoverKeyResponse>
      <serialNumber>{serial}</serialNumber>
      <recoveredKey>KEY-FOR-{serial}</recoveredKey>
      <status>SUCCESS</status>
    </RecoverKeyResponse>
  </soap:Body>
</soap:Envelope>'''
                print('\n--- Mock SOAP Server sending KEY RECOVERY response ---')
                print(resp)
                await ws.send(resp)
                continue

            # Certificate Queries
            if 'FindCertsRequest' in message:
                resp = '''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <FindCertsResponse>
      <certificate>MIIDFA...</certificate>
      <certificate>MIIDGB...</certificate>
    </FindCertsResponse>
  </soap:Body>
</soap:Envelope>'''
                print('\n--- Mock SOAP Server sending CERT QUERY response ---')
                print(resp)
                await ws.send(resp)
                continue

            if 'GetCertificateRequest' in message:
                resp = '''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetCertificateResponse>
      <serialNumber>12345</serialNumber>
      <certificate>MIIFAKECERT...</certificate>
    </GetCertificateResponse>
  </soap:Body>
</soap:Envelope>'''
                print('\n--- Mock SOAP Server sending SINGLE CERT response ---')
                print(resp)
                await ws.send(resp)
                continue

            if 'GetLastCAChainRequest' in message:
                resp = '''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetLastCAChainResponse>
      <caCertificate>MIICACHAINCERT...</caCertificate>
    </GetLastCAChainResponse>
  </soap:Body>
</soap:Envelope>'''
                print('\n--- Mock SOAP Server sending CA CHAIN response ---')
                print(resp)
                await ws.send(resp)
                continue

            # Fallback
            resp = '''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GenericResponse>
      <message>Unknown request handled</message>
    </GenericResponse>
  </soap:Body>
</soap:Envelope>'''
            print('\n--- Mock SOAP Server sending GENERIC response ---')
            print(resp)
            await ws.send(resp)

    except websockets.ConnectionClosed:
        print('Connection closed')
    except Exception as e:
        print('Mock server error:', e)


if __name__ == '__main__':
    print(f'Starting mock SOAP websocket server at ws://{HOST}:{PORT}')

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)
    ssl_context.load_verify_locations(cafile=CA_PATH)
    ssl_context.verify_mode = ssl.CERT_REQUIRED # Enfore client cert

    async def main():
        async with websockets.serve(handle, HOST, PORT, ssl=ssl_context):
            await asyncio.Future()  # run forever

    asyncio.run(main())
