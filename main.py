import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
WP_URL     = os.getenv("WP_URL")     # ex: https://virtualizedmind.com
RM_API_KEY = os.getenv("RM_API_KEY") # tu clave secreta

if not (WP_URL and RM_API_KEY):
    raise RuntimeError("Faltan WP_URL o RM_API_KEY en el entorno")

app = FastAPI()

class Item(BaseModel):
    url: str

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/upload_media")
def upload_media(item: Item):
    # Construye petición
    endpoint = f"{WP_URL.rstrip('/')}/wp-json/rm/v1/sideload"
    headers  = {"X-RM-API-KEY": RM_API_KEY}
    payload  = {"url": item.url}

    try:
        r = requests.post(endpoint, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as exc:
        code = exc.response.status_code
        detail = exc.response.text
        raise HTTPException(status_code=code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
