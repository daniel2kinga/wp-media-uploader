import os
import base64
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv

# Carga las variables definidas en .env o en el entorno
load_dotenv()
WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
    raise RuntimeError("Faltan WP_URL, WP_USER o WP_APP_PASSWORD en .env")

# Prepara la cabecera de Basic Auth para WordPress
credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
token = base64.b64encode(credentials.encode()).decode()
HEADERS = {"Authorization": f"Basic {token}"}

app = FastAPI()

class Item(BaseModel):
    url: str

def get_filename(path_or_url: str) -> str:
    """Extrae el nombre de fichero (con extensión) de una URL o ruta local."""
    parsed = urlparse(path_or_url)
    return os.path.basename(parsed.path)

def download_image(url: str) -> bytes:
    """Descarga los bytes de la imagen desde la URL dada."""
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.content

@app.post("/upload_media")
def upload_media_endpoint(item: Item):
    """
    Endpoint que recibe JSON {"url": "..."} y sube esa imagen a WP Media.
    Devuelve {"id": <media_id>, "source_url": "<url_publica>"}.
    """
    try:
        # 1) Descargar la imagen
        data = download_image(item.url)
        filename = get_filename(item.url)

        # 2) Hacer POST a la REST API de WordPress /wp-json/wp/v2/media
        upload_url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/media"
        headers = {
            **HEADERS,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/octet-stream"
        }
        resp = requests.post(upload_url, data=data, headers=headers)
        resp.raise_for_status()

        j = resp.json()
        return {"id": j["id"], "source_url": j["source_url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    """Endpoint de comprobación de vida."""
    return {"status": "ok"}
