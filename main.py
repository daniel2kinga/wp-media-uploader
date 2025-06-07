import os
import mimetypes
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# 1) Carga .env o variables de entorno de Railway
load_dotenv()
WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

if not (WP_URL and WP_USER and WP_APP_PASSWORD):
    raise RuntimeError("Faltan WP_URL, WP_USER o WP_APP_PASSWORD en el entorno")

# 2) Prepara autenticación
AUTH = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

app = FastAPI()

class Item(BaseModel):
    url: str

def get_filename(path_or_url: str) -> str:
    parsed = urlparse(path_or_url)
    return os.path.basename(parsed.path)

def download_image(url: str) -> bytes:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.content

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/whoami")
def whoami():
    """
    Endpoint de debug: comprueba credenciales obteniendo el usuario actual.
    """
    url = WP_URL.rstrip("/") + "/wp-json/wp/v2/users/me"
    resp = requests.get(url, auth=AUTH)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Auth check failed: {resp.status_code} {resp.text}"
        )
    return resp.json()

@app.post("/upload_media")
def upload_media_endpoint(item: Item):
    try:
        # --- 1) Descarga la imagen ---
        data = download_image(item.url)
        filename = get_filename(item.url)

        # --- 2) Detecta Content-Type según extensión ---
        ctype, _ = mimetypes.guess_type(filename)
        if not ctype:
            ctype = "application/octet-stream"

        # --- 3) Prepara la subida a WP ---
        upload_url = WP_URL.rstrip("/") + "/wp-json/wp/v2/media"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": ctype
        }

        # --- 4) Ejecuta la petición POST con Basic Auth ---
        resp = requests.post(upload_url, data=data, headers=headers, auth=AUTH)

        # --- 5) Si da 403, levantamos detalle claro ---
        if resp.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="403 Forbidden. Comprueba WP_USER / WP_APP_PASSWORD "
                       "y que la API de Application Passwords esté activa."
            )

        resp.raise_for_status()
        result = resp.json()
        return {"id": result["id"], "source_url": result["source_url"]}

    except HTTPException:
        # Propaga nuestro 403 personalizado u otros HTTPException
        raise
    except Exception as e:
        # Errores genéricos
        raise HTTPException(status_code=500, detail=str(e))
