from fastapi import FastAPI, Request, HTTPException
import logging
import ssl
import http.client
import xml.etree.ElementTree as ET
from xml.dom import minidom

app = FastAPI()

logger = logging.getLogger("ejbca-proxy")
logger.setLevel(logging.INFO)

# EBCA SOAP endpoint details
HOST = "localhost"
PORT = 8443
SOAP_PATH = "/ejbcaws/ejbcaws"

CERT_PATH = "certs/proxy.crt"
KEY_PATH = "certs/proxy.key"
CAPATH = "certs/CAFull.crt"

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
EJBCA_NS = "http://ws.protocol.core.ejbca.org/"

ET.register_namespace('soap', SOAP_NS)
ET.register_namespace('ejbca', EJBCA_NS)

# Build SOAP envelope from JSON
def build_soap_envelope(operation: str, payload: dict) -> str:
    envelope = ET.Element(f"{{{SOAP_NS}}}Envelope")
    body = ET.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    op_el = ET.SubElement(body, f"{{{EJBCA_NS}}}{operation}")

    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, list):
            for item in v:
                sub_el = ET.SubElement(op_el, k)
                if isinstance(item, dict):
                    for sub_k, sub_v in item.items():
                        ET.SubElement(sub_el, sub_k).text = str(sub_v)
                else:
                    sub_el.text = str(item)
        else:
            ET.SubElement(op_el, k).text = str(v)

    rough = ET.tostring(envelope, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="    ")
    logger.info("Generated SOAP XML:\n%s", pretty)
    return pretty

# Parse SOAP response into dict
'''
def parse_soap_response(xml_text: str) -> dict:
    try:
        root = ET.fromstring(xml_text)
        body = root.find(f".//{{{SOAP_NS}}}Body")
        if body is None or len(body) == 0:
            return {"error": "No SOAP Body"}
        first = list(body)[0]
        result = {child.tag: child.text for child in first}
        return {first.tag: result}
    except ET.ParseError as e:
        return {"error": f"XML parse error: {e}"}
'''
def parse_soap_response(xml_text: str) -> dict:
    if not xml_text.strip().startswith("<"):
        return {"error": "Response is not XML", "body": xml_text[:200]}
    try:
        root = ET.fromstring(xml_text)
        if root.tag != f"{{{SOAP_NS}}}Envelope":
            return {"error": "Response is not a SOAP Envelope", "body": xml_text[:200]}
        body = root.find(f".//{{{SOAP_NS}}}Body")
        if body in None:
            return {"error": "No SOAP body element found"}
        except ET.ParseError as e:
            return {"error": "XML parse error: {e}", "body": xml_text[:200]}

# Send SOAP over HTTPS using http.client with mTLS
def send_soap_request(operation: str, soap_xml: str) -> str:
    try:
        context = ssl.create_default_context(cafile=CAPATH)
        context.load_cert_chain(certfile=CERT_PATH, keyfile=KEY_PATH)
        conn = http.client.HTTPSConnection(HOST, PORT, context=context)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f"http://ws.protocol.core.ejbca.org/{operation}"
        }
        conn.request("POST", SOAP_PATH, body=soap_xml.encode("utf-8"), headers=headers)
        response = conn.getresponse()
        resp_data = response.read().decode("utf-8")
        conn.close()
        return resp_data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error communicating with SOAP WS: {e}")

@app.post("/v1/certificate/certificaterequest")
async def certificate_request(req: Request):
    data = await req.json()
    logger.info("Received certificate request: %s", data)
    soap_xml = build_soap_envelope("certificateRequest", data)
    soap_rsp = send_soap_request("certificateRequest", soap_xml)
    parsed = parse_soap_response(soap_rsp)
    if "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed)
    return parsed

@app.post("/v1/certificate/search")
async def certificate_search(req: Request):
    data = await req.json()
    logger.info("Received certificate search: %s", data)
    soap_xml = build_soap_envelope("findCerts", data)
    soap_rsp = send_soap_request("findCerts", soap_xml)
    parsed = parse_soap_response(soap_rsp)
    if "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed)
    return parsed

@app.post("/v1/endentity")
async def end_entity(req: Request):
    data = await req.json()
    logger.info("Received end entity request: %s", data)
    soap_xml = build_soap_envelope("editUser", data)
    soap_rsp = send_soap_request("editUser", soap_xml)
    parsed = parse_soap_response(soap_rsp)
    if "error" in parsed:
        raise HTTPException(status_code=400, detail=parsed)
    return parsed

@app.get("/health")
async def health():
    return {"status": "ok"}
