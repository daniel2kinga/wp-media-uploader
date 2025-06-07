import os
import base64
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv

# Carga .env
load_dotenv()
WP_URL = os.getenv("https://virtualizedmind.com/")
WP_USER = os.getenv("daniel2kinga_iiorc19b")
WP_APP_PASSWORD = os.getenv("UWSy koAz YNQK Gwnf GbEs LRbt")

if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
    raise RuntimeError("Faltan WP_URL, WP_USER o WP_APP_PASSWORD en .env")

# Prepara Basic Auth
credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
token = base64.b64encode(credentials.encode()).decode()
HEADERS = {"Authorization": f"Basic {token}"}

app = FastAPI()

class Item(BaseModel):
    url: str

def get_filename(path_or_url: str) -> str:
    return os.path.basename(urlparse(path_or_url).path)

def download_image(url: str) -> bytes:
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.content

@app.post("/upload_media")
def upload_media_endpoint(item: Item):
    try:
        data = download_image(item.url)
        filename = get_filename(item.url)
        # sube vía WP REST API
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
    return {"status": "ok"}
