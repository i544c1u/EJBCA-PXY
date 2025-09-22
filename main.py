# File: main.py
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import logging
import ssl
import asyncio
import websockets
import xml.etree.ElementTree as ET

logger = logging.getLogger("ejbca-pxy")
logger.setLevel(logging.INFO)

app = FastAPI()
SOAP_WS_URI = 'wss://localhost:8888'

CERT_PATH = 'certs/client.crt'
KEY_PATH = 'certs/client.key'
CA_PATH = 'certs/ca.crt'

class RecoverRequest(BaseModel):
    serialNumber: str
    username: str

class KeyRecoveryEnrollRequest(BaseModel):
    serialNumber: str
    username: str
    enrollmentCode: str

# SOAP builders
def build_recover_soap(serial: str, username: str) -> str:
    return f'''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <RecoverKeyRequest>
      <serialNumber>{serial}</serialNumber>
      <username>{username}</username>
    </RecoverKeyRequest>
  </soap:Body>
</soap:Envelope>'''

def to_soap(root_tag: str, payload: dict) -> str:
    env = ET.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope",
                        nsmap={'soap': 'http://schemas.xmlsoap.org/soap/envelope/'})
    body = ET.SubElement(env, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
    main = ET.SubElement(body, root_tag)
    for k, v in payload.items():
        ET.SubElement(main, k).text = str(v)
    return ET.tostring(env, encoding="utf-8", xml_declaration=True).decode()

# SOAP parser
def parse_soap_response(xml_text: str) -> dict:
    try:
        ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
        root = ET.fromstring(xml_text)
        body = root.find('soap:Body', ns)
        if body is None:
            return {'error': 'No SOAP Body'}

        fault = body.find('soap:Fault', ns)
        if fault is not None:
            faultstring = fault.find('faultstring')
            return {'fault': faultstring.text if faultstring is not None else 'Unknown fault'}

        # Extract first child as dict
        first = list(body)[0]
        out = {}
        for child in first:
            out[child.tag] = child.text
        return {first.tag: out}

    except ET.ParseError as e:
        return {'error': f'XML parse error: {e}'}

async def send_soap_over_ws(soap_path: str, soap_xml: str, timeout: float = 5.0) -> str:
    logger.debug("PATH: %s\nCONTENT: %s", soap_path, soap_xml)
    try:
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA_PATH)
        ssl_context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)
        logger.info("SOAP req to: %s", SOAP_WS_URI + soap_path)
        async with websockets.connect(SOAP_WS_URI + soap_path, ssl=ssl_context) as ws:
            await ws.send(soap_xml)
            resp = await asyncio.wait_for(ws.recv(), timeout)
            return resp
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail='Timeout waiting for SOAP response')
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'Error communicating with SOAP WS: {e}')

# Endpoints
@app.post("/v1/certificate/certificaterequest")
async def cert_req(req: Request):
    data = await req.json()
    logger.info("Received certificate request: %s", data)

    soap_req = to_soap("certificaterequest", data)
    soap_rsp = await send_soap_over_ws("/certificate/certificaterequest", soap_req)

    parsed = parse_soap_response(soap_rsp)
    if 'fault' in parsed:
        raise HTTPException(status_code=400, detail={'soap_fault': parsed['fault']})
    return parsed

@app.post("/v1/certificate/search")
async def cert_search(req: Request):
    data = await req.json()
    logger.info("Received certificate search: %s", data)

    soap_req = to_soap("certificatesearch", data)
    soap_rsp = await send_soap_over_ws("/certificate/search", soap_req)

    parsed = parse_soap_response(soap_rsp)
    if 'fault' in parsed:
        raise HTTPException(status_code=400, detail={'soap_fault': parsed['fault']})
    return parsed

@app.post("/v1/endentity")
async def end_entity(req: Request):
    data = await req.json()
    logger.info("Received endentity request: %s", data)

    soap_req = to_soap("endentity", data)
    soap_rsp = await send_soap_over_ws("/endentity", soap_req)

    parsed = parse_soap_response(soap_rsp)
    if 'fault' in parsed:
        raise HTTPException(status_code=400, detail={'soap_fault': parsed['fault']})
    return parsed

@app.get('/health')
async def health():
    return {'status': 'ok'}
