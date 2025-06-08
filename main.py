import os
import mimetypes
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# 1) Carga de configuración
load_dotenv()
WP_URL          = os.getenv("WP_URL")           # ej. https://virtualizedmind.com
WP_USER         = os.getenv("WP_USER")          # tu usuario de WP
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")  # tu Application Password (4 grupos)

if not (WP_URL and WP_USER and WP_APP_PASSWORD):
    raise RuntimeError("Faltan WP_URL, WP_USER o WP_APP_PASSWORD en el entorno")

# 2) Prepara Basic Auth
AUTH = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

app = FastAPI()

class Item(BaseModel):
    url: str

def get_filename(url: str) -> str:
    return os.path.basename(urlparse(url).path)

def download_image(url: str) -> bytes:
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    return r.content

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/upload_media")
def upload_media(item: Item):
    """
    1) Descarga la imagen desde item.url
    2) La sube a /wp-json/wp/v2/media usando multipart/form-data
    3) Devuelve {id, source_url}
    """
    try:
        # Descarga
        data = download_image(item.url)
        filename = get_filename(item.url)

        # Detecta MIME
        ctype, _ = mimetypes.guess_type(filename)
        if not ctype:
            ctype = "application/octet-stream"

        # Multipart upload a WP
        files = {"file": (filename, data, ctype)}
        resp = requests.post(
            f"{WP_URL.rstrip('/')}/wp-json/wp/v2/media",
            files=files,
            auth=AUTH
        )
        resp.raise_for_status()
        j = resp.json()
        return {"id": j["id"], "source_url": j["source_url"]}

    except requests.HTTPError as he:
        code = he.response.status_code
        detail = he.response.text
        raise HTTPException(status_code=code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
