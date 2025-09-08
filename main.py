# File: main.py
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import asyncio
import websockets
import xml.etree.ElementTree as ET

app = FastAPI()
SOAP_WS_URI = 'ws://localhost:8888'

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

def build_keyrecovery_enroll_soap(serial: str, username: str, enrollmentCode: str) -> str:
    return f'''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <KeyRecoveryEnrollRequest>
      <serialNumber>{serial}</serialNumber>
      <username>{username}</username>
      <enrollmentCode>{enrollmentCode}</enrollmentCode>
    </KeyRecoveryEnrollRequest>
  </soap:Body>
</soap:Envelope>'''

def build_cert_query_soap(request_type: str) -> str:
    return f'''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{request_type}/>
  </soap:Body>
</soap:Envelope>'''

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

async def send_soap_over_ws(soap_xml: str, timeout: float = 5.0) -> str:
    try:
        async with websockets.connect(SOAP_WS_URI) as ws:
            await ws.send(soap_xml)
            resp = await asyncio.wait_for(ws.recv(), timeout)
            return resp
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail='Timeout waiting for SOAP response')
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'Error communicating with SOAP WS: {e}')

# Endpoints
@app.post('/recover_key')
async def recover_key(req: RecoverRequest):
    soap_request = build_recover_soap(req.serialNumber, req.username)
    print('\n--- Adapter sending SOAP (recover_key) ---')
    print(soap_request)
    soap_resp = await send_soap_over_ws(soap_request)
    print('\n--- Adapter received SOAP (recover_key) ---')
    print(soap_resp)
    parsed = parse_soap_response(soap_resp)
    if 'fault' in parsed:
        raise HTTPException(status_code=400, detail={'soap_fault': parsed['fault']})
    return parsed

@app.post('/key_recovery_enroll')
async def key_recovery_enroll(req: KeyRecoveryEnrollRequest):
    soap_request = build_keyrecovery_enroll_soap(req.serialNumber, req.username, req.enrollmentCode)
    print('\n--- Adapter sending SOAP (key_recovery_enroll) ---')
    print(soap_request)
    soap_resp = await send_soap_over_ws(soap_request)
    print('\n--- Adapter received SOAP (key_recovery_enroll) ---')
    print(soap_resp)
    parsed = parse_soap_response(soap_resp)
    if 'fault' in parsed:
        raise HTTPException(status_code=400, detail={'soap_fault': parsed['fault']})
    return parsed

@app.post('/cert_query/{query_type}')
async def cert_query(query_type: str):
    soap_request = build_cert_query_soap(query_type)
    print(f'\n--- Adapter sending SOAP ({query_type}) ---')
    print(soap_request)
    soap_resp = await send_soap_over_ws(soap_request)
    print(f'\n--- Adapter received SOAP ({query_type}) ---')
    print(soap_resp)
    parsed = parse_soap_response(soap_resp)
    if 'fault' in parsed:
        raise HTTPException(status_code=400, detail={'soap_fault': parsed['fault']})
    return parsed

@app.post('/soap-to-json')
async def soap_to_json(request: Request):
    body = await request.body()
    text = body.decode('utf-8')
    print('\n--- Adapter received raw SOAP (soap-to-json) ---')
    print(text)
    parsed = parse_soap_response(text)
    if 'error' in parsed:
        raise HTTPException(status_code=400, detail=parsed['error'])
    return parsed

@app.get('/health')
async def health():
    return {'status': 'ok'}
