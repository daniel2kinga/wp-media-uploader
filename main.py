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
WP_URL          = os.getenv("WP_URL")           # e.g. https://virtualizedmind.com
WP_USER         = os.getenv("WP_USER")          # tu login de WP
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")  # tu Application Password nativo de WP

if not (WP_URL and WP_USER and WP_APP_PASSWORD):
    raise RuntimeError("Faltan WP_URL, WP_USER o WP_APP_PASSWORD en el entorno")

# 2) Prepara Basic Auth con Application Passwords
AUTH = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

app = FastAPI()

class Item(BaseModel):
    url: str

def get_filename(url: str) -> str:
    return os.path.basename(urlparse(url).path)

def download_image(url: str) -> bytes:
    resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
    resp.raise_for_status()
    return resp.content

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload_media")
def upload_media(item: Item):
    """
    1) Descarga la imagen desde item.url
    2) Sube usando multipart/form-data a /wp-json/wp/v2/media
    3) Devuelve {id, source_url}
    """
    try:
        # --- 1) Descarga ---
        data = download_image(item.url)
        filename = get_filename(item.url)

        # --- 2) Detecta Content-Type ---
        ctype, _ = mimetypes.guess_type(filename)
        if not ctype:
            ctype = "application/octet-stream"

        # --- 3) Prepara multipart upload ---
        files = {
            'file': (filename, data, ctype)
        }
        upload_endpoint = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/media"

        resp = requests.post(
            upload_endpoint,
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
