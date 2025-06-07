import os
import base64
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv

# Carga variables de entorno de .env o del entorno de Railway
load_dotenv()
WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

if not WP_URL or not WP_USER or not WP_APP_PASSWORD:
    raise RuntimeError("Faltan WP_URL, WP_USER o WP_APP_PASSWORD en el entorno")

# Prepara Basic Auth para WordPress REST API
credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
token = base64.b64encode(credentials.encode()).decode()
HEADERS = {"Authorization": f"Basic {token}"}

app = FastAPI()

class Item(BaseModel):
    url: str

def get_filename(path_or_url: str) -> str:
    """Extrae el nombre de archivo (con extensión) de una URL o ruta."""
    return os.path.basename(urlparse(path_or_url).path)

def download_image(url: str) -> bytes:
    """Descarga los bytes de la imagen desde la URL dada."""
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.content

@app.get("/health")
def health():
    """Endpoint de verificación: devuelve {"status":"ok"}."""
    return {"status": "ok"}

@app.post("/upload_media")
def upload_media_endpoint(item: Item):
    """
    Recibe JSON { "url": "<imagen_url>" },
    descarga la imagen y la sube a WordPress Media Library.
    Devuelve { "id": <media_id>, "source_url": "<URL pública>" }.
    """
    try:
        # 1) Descargar
        data = download_image(item.url)
        filename = get_filename(item.url)

        # 2) Subir a WP
        upload_url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/media"
        headers = {
            **HEADERS,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/octet-stream"
        }
        resp = requests.post(upload_url, data=data, headers=headers)
        resp.raise_for_status()

        result = resp.json()
        return {"id": result["id"], "source_url": result["source_url"]}

    except Exception as e:
        # Devuelve mensaje de error al cliente
        raise HTTPException(status_code=500, detail=str(e))
