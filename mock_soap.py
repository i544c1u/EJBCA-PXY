#!/usr/bin/env python3
"""
soap_ws_mock.py

A pure websockets/asyncio server that accepts SOAP-style XML over WebSocket
and replies with SOAP XML envelopes.

Run:
    python soap_ws_mock.py
Requires:
    pip install websockets
"""

import asyncio
import websockets
import logging
import ssl
import uuid
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("soap-ws-mock")

HOST = 'localhost'
PORT = 8888

CERT_PATH = 'certs/server.crt'
KEY_PATH = 'certs/server.key'
CA_PATH = 'certs/ca.crt'

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SOAP_PREFIX = "{%s}" % SOAP_NS

ET.register_namespace("soap", SOAP_NS)


def soap_envelope(body_el: ET.Element) -> str:
    """Wrap an XML element inside a SOAP Envelope/Body."""
    envelope = ET.Element(f"{SOAP_PREFIX}Envelope")
    body = ET.SubElement(envelope, f"{SOAP_PREFIX}Body")
    body.append(body_el)
    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True).decode()


def parse_soap(xml_text: str) -> ET.Element:
    """Return first element inside <soap:Body>."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}") from e

    body = root.find(f".//{SOAP_PREFIX}Body")
    if body is None or len(body) == 0:
        raise ValueError("No SOAP Body found")
    return list(body)[0]


def xml_error_response(code: str, message: str, extra: dict = None) -> str:
    """Build a SOAP error response with given error code and message."""
    err = ET.Element("ErrorResponse")
    ET.SubElement(err, "error_code").text = code
    ET.SubElement(err, "error_message").text = message
    if extra:
        for k, v in extra.items():
            ET.SubElement(err, k).text = str(v)
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

        csr = inner.findtext("CSR")
        username = inner.findtext("Username")
        if not csr or not username:
            resp = xml_error_response("422", "Missing required field: CSR and Username are required")
            await ws.send(resp)
            continue

        request_id = str(uuid.uuid4())
        resp_body = ET.Element("CertificateRequestResponse")
        ET.SubElement(resp_body, "status").text = "OK"
        ET.SubElement(resp_body, "requestId").text = request_id
        ET.SubElement(resp_body, "username").text = username
        ET.SubElement(resp_body, "message").text = "CSR accepted (SOAP WS mock)"
        await ws.send(soap_envelope(resp_body))


async def handle_search(ws):
    async for msg in ws:
        logger.info("Search SOAP received")
        try:
            inner = parse_soap(msg)
            username = inner.findtext("Username") or "unknown"
        except Exception as e:
            err = ET.Element("Error")
            err.text = f"Parse error: {e}"
            await ws.send(soap_envelope(err))
            continue

        resp = ET.Element("SearchResponse")
        items = ET.SubElement(resp, "items")
        item = ET.SubElement(items, "item")
        ET.SubElement(item, "certificateId").text = str(uuid.uuid4())
        ET.SubElement(item, "username").text = username
        ET.SubElement(item, "status").text = "ISSUED"
        await ws.send(soap_envelope(resp))


async def handle_endentity(ws):
    async for msg in ws:
        logger.info("EndEntity SOAP received")
        try:
            inner = parse_soap(msg)
            username = inner.findtext("Username") or "unknown"
        except Exception as e:
            err = ET.Element("Error")
            err.text = f"Parse error: {e}"
            await ws.send(soap_envelope(err))
            continue

        resp = ET.Element("EndEntityResponse")
        ET.SubElement(resp, "status").text = "OK"
        ET.SubElement(resp, "username").text = username
        ET.SubElement(resp, "message").text = "End entity processed (SOAP WS mock)"
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
        err = ET.Element("Error")
        err.text = f"Unknown path {path}"
        await ws.send(soap_envelope(err))
        await ws.close()


if __name__ == "__main__":
    logger.info("Starting WebSocket mock server on %s:%d", HOST, PORT)
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)
    ssl_context.load_verify_locations(cafile=CA_PATH)
    ssl_context.verify_mode = ssl.CERT_REQUIRED  # Enforce client cert

    async def main():
        async with websockets.serve(dispatch, HOST, PORT, ssl=ssl_context):
            await asyncio.Future()  # run forever

    asyncio.run(main())
