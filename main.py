import os
import mimetypes
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# 1) Carga variables de entorno (.env local o Railway)
load_dotenv()
WP_URL = os.getenv("WP_URL")               # p.ej. https://virtualizedmind.com
WP_USER = os.getenv("WP_USER")             # tu login de WP
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")  # tu contraseña de WP (no Application Password)

if not (WP_URL and WP_USER and WP_APP_PASSWORD):
    raise RuntimeError("Faltan WP_URL, WP_USER o WP_APP_PASSWORD en el entorno")

# 2) Prepara objeto de Autenticación Básica
AUTH = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

app = FastAPI()

class Item(BaseModel):
    url: str

def get_filename(path_or_url: str) -> str:
    """Extrae nombre de fichero (con extensión) desde la URL."""
    return os.path.basename(urlparse(path_or_url).path)

def download_image(url: str) -> bytes:
    """Descarga la imagen desde la URL dada."""
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.content

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload_media")
def upload_media(item: Item):
    """
    1) Recibe JSON {"url": "..."}.
    2) Descarga la imagen.
    3) La sube a /wp-json/wp/v2/media con Basic Auth.
    4) Devuelve {"id":..., "source_url": "..."}.
    """
    try:
        # Descarga
        img_data = download_image(item.url)
        filename = get_filename(item.url)

        # Detectar MIME type
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "application/octet-stream"

        # Subida REST API
        upload_endpoint = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/media"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": content_type
        }

        resp = requests.post(
            upload_endpoint,
            data=img_data,
            headers=headers,
            auth=AUTH
        )
        resp.raise_for_status()  # lanzará HTTPError si no es 2xx

        result = resp.json()
        return {"id": result["id"], "source_url": result["source_url"]}

    except requests.HTTPError as he:
        # Capturar 403/401 y resto de HTTP
        code = he.response.status_code
        detail = he.response.text
        raise HTTPException(status_code=code, detail=f"{code} {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
