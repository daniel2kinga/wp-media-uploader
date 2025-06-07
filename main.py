import os
import mimetypes
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# XML-RPC
from wordpress_xmlrpc import Client as WPClient
from wordpress_xmlrpc.methods import media as xmlrpc_media
from wordpress_xmlrpc.compat import xmlrpc_client

# Carga .env o variables de Railway
load_dotenv()
WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

if not (WP_URL and WP_USER and WP_APP_PASSWORD):
    raise RuntimeError("Faltan WP_URL, WP_USER o WP_APP_PASSWORD en el entorno")

# Autenticación para REST
AUTH = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)
# Cliente para XML-RPC
XMLRPC = WPClient(f"{WP_URL.rstrip('/')}/xmlrpc.php", WP_USER, WP_APP_PASSWORD)

app = FastAPI()

class Item(BaseModel):
    url: str

def get_filename(path_or_url: str) -> str:
    return os.path.basename(urlparse(path_or_url).path)

def download_image(url: str) -> bytes:
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.content

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/whoami")
def whoami():
    url = WP_URL.rstrip("/") + "/wp-json/wp/v2/users/me"
    r = requests.get(url, auth=AUTH)
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"Auth failed: {r.status_code} {r.text}")
    return r.json()

@app.post("/upload_media")
def upload_media_endpoint(item: Item):
    """
    1) Intenta subir por REST API con Application Passwords.
    2) Si da 403, hace fallback a XML-RPC.
    """
    data = download_image(item.url)
    filename = get_filename(item.url)

    # Determinar MIME type
    ctype, _ = mimetypes.guess_type(filename)
    if not ctype:
        ctype = "application/octet-stream"

    # 1) Intentar REST API
    rest_url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/media"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": ctype
    }
    try:
        r = requests.post(rest_url, data=data, headers=headers, auth=AUTH)
        if r.status_code == 403:
            raise PermissionError("REST returned 403, haciendo fallback a XML-RPC")
        r.raise_for_status()
        j = r.json()
        return {"id": j["id"], "source_url": j["source_url"], "via": "rest"}
    except PermissionError:
        # Fallback a XML-RPC
        binary = xmlrpc_client.Binary(data)
        xmlrpc_data = {
            "name": filename,
            "type": ctype,
            "bits": binary
        }
        resp = XMLRPC.call(xmlrpc_media.UploadFile(xmlrpc_data))
        # resp es un dict con keys 'id' y 'file' (ruta relativa)
        source = f"{WP_URL.rstrip('/')}/wp-content/uploads/{resp['file']}"
        return {"id": resp["id"], "source_url": source, "via": "xmlrpc"}
    except Exception as e:
        # Si r.raise_for_status() falla con otro código
        # u otro error, devolvemos HTTP 500
        raise HTTPException(status_code=500, detail=str(e))
