"""
> Refer to: https://docs.keyfactor.com/ejbca/latest/open-api-specification
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
"""

#!/usr/bin/env python3
"""
soap_ws_mock.py

A pure websockets/asyncio server that accepts SOAP-style XML over WebSocket
and replies with SOAP XML envelopes.

Run:
    python soap_ws_mock.py
Requires:
    pip install websockets lxml
"""

import asyncio
import websockets
import logging
import ssl
import uuid
from lxml import etree

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("soap-ws-mock")

HOST = 'localhost'
PORT = 8888

CERT_PATH = 'certs/server.crt'
KEY_PATH = 'certs/server.key'
CA_PATH = 'certs/ca.crt'

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"

def soap_envelope(body_el: etree.Element) -> str:
    """Wrap an XML element inside a SOAP Envelope/Body."""
    envelope = etree.Element("{%s}Envelope" % SOAP_NS, nsmap={"soap": SOAP_NS})
    body = etree.SubElement(envelope, "{%s}Body" % SOAP_NS)
    body.append(body_el)
    return etree.tostring(envelope, encoding="utf-8", xml_declaration=True).decode()

def parse_soap(xml_text: str) -> etree.Element:
    """Return first element inside <soap:Body>."""
    root = etree.fromstring(xml_text.encode())
    body = root.find(".//{%s}Body" % SOAP_NS)
    if body is None or len(body) == 0:
        raise ValueError("No SOAP Body found")
    return body[0]

def xml_error_response(code: str, message: str, extra: dict = None) -> str:
    """
    Build a SOAP error response with given error code and message.
    extra can include other child elements.
    """
    err = etree.Element("ErrorResponse")
    etree.SubElement(err, "error_code").text = code
    etree.SubElement(err, "error_message").text = message
    if extra:
        for k, v in extra.items():
            etree.SubElement(err, k).text = str(v)
    return soap_envelope(err)

async def handle_certificaterequest(ws):
    async for msg in ws:
        logger.info("WS CertRequest received message: %s", msg[:200])
        try:
            inner = parse_soap(msg)
        except ValueError as ve:
            resp = xml_error_response("400", f"Invalid request XML: {ve}")
            await ws.send(resp)
            continue

        # validate required fields
        csr = inner.findtext("CSR")
        username = inner.findtext("Username")
        if not csr or not username:
            resp = xml_error_response("422", "Missing required field: CSR and Username are required")
            await ws.send(resp)
            continue

        # Ok path
        request_id = str(uuid.uuid4())
        resp_body = etree.Element("CertificateRequestResponse")
        etree.SubElement(resp_body, "status").text = "OK"
        etree.SubElement(resp_body, "requestId").text = request_id
        etree.SubElement(resp_body, "username").text = username
        etree.SubElement(resp_body, "message").text = "CSR accepted (SOAP WS mock)"
        await ws.send(soap_envelope(resp_body))

async def handle_search(ws):
    async for msg in ws:
        logger.info("Search SOAP received")
        try:
            inner = parse_soap(msg)
            username = inner.findtext("Username", default="unknown")
        except Exception as e:
            err = etree.Element("Error")
            err.text = f"Parse error: {e}"
            await ws.send(soap_envelope(err))
            continue

        resp = etree.Element("SearchResponse")
        items = etree.SubElement(resp, "items")
        item = etree.SubElement(items, "item")
        etree.SubElement(item, "certificateId").text = str(uuid.uuid4())
        etree.SubElement(item, "username").text = username
        etree.SubElement(item, "status").text = "ISSUED"
        await ws.send(soap_envelope(resp))

async def handle_endentity(ws):
    async for msg in ws:
        logger.info("EndEntity SOAP received")
        try:
            inner = parse_soap(msg)
            username = inner.findtext("Username", default="unknown")
        except Exception as e:
            err = etree.Element("Error")
            err.text = f"Parse error: {e}"
            await ws.send(soap_envelope(err))
            continue

        resp = etree.Element("EndEntityResponse")
        etree.SubElement(resp, "status").text = "OK"
        etree.SubElement(resp, "username").text = username
        etree.SubElement(resp, "message").text = "End entity processed (SOAP WS mock)"
        await ws.send(soap_envelope(resp))

async def dispatch(ws):
    path = ws.request.path
    logger.info("New WS connection path=%s", path)
    if path == "/certificate/certificaterequest":
        await handle_certificaterequest(ws)
    elif path == "/certificate/search":
        await handle_search(ws)
    elif path == "/endentity":
        await handle_endentity(ws)
    else:
        err = etree.Element("Error")
        err.text = f"Unknown path {path}"
        await ws.send(soap_envelope(err))
        await ws.close()

if __name__ == "__main__":
    logger.info("Starting WebSocket mock server on %s:%d", HOST, PORT)
    # mTLS Settiings
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)
    ssl_context.load_verify_locations(cafile=CA_PATH)
    ssl_context.verify_mode = ssl.CERT_REQUIRED # Enfore client cert

    async def main():
        async with websockets.serve(dispatch, HOST, PORT, ssl=ssl_context):
            await asyncio.Future()  # run forever

    asyncio.run(main())
