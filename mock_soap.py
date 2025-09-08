"""
# Recover key
curl -X POST http://localhost:8666/recover_key \
     -H "Content-Type: application/json" \
     -d '{"serialNumber":"12345","username":"alice"}'

# Key recovery enrollment
curl -X POST http://localhost:8666/key_recovery_enroll \
     -H "Content-Type: application/json" \
     -d '{"serialNumber":"12345","username":"alice","enrollmentCode":"xyz"}'

curl -X POST "http://localhost:8666/soap-to-json" -H "Content-Type: text/xml" --data-binary @sample_request.xml

# Certificate queries
curl -X POST http://localhost:8666/cert_query/FindCertsRequest
curl -X POST http://localhost:8666/cert_query/GetCertificateRequest
curl -X POST http://localhost:8666/cert_query/GetLastCAChainRequest
"""

# File: mock_soap.py
import asyncio
import websockets

HOST = 'localhost'
PORT = 8888

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

    async def main():
        async with websockets.serve(handle, HOST, PORT):
            await asyncio.Future()  # run forever

    asyncio.run(main())
