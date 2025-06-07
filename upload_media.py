#!/usr/bin/env python3
"""
upload_media.py

Sube una imagen a la biblioteca de medios de WordPress usando Application Passwords.
Puede tomar una ruta local o una URL remota de imagen.
"""

import os
import sys
import argparse
import base64
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

# Carga WP_URL, WP_USER y WP_APP_PASSWORD de .env
load_dotenv()
WP_URL = os.getenv("WP_URL")
WP_USER = os.getenv("WP_USER")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
    print("❌ Asegúrate de definir WP_URL, WP_USER y WP_APP_PASSWORD en .env")
    sys.exit(1)

# Prepara la cabecera Basic Auth
credentials = f"{WP_USER}:{WP_APP_PASSWORD}"
token = base64.b64encode(credentials.encode()).decode()
HEADERS = {
    "Authorization": f"Basic {token}"
}

def get_filename_from_path_or_url(path_or_url: str) -> str:
    """Extrae el nombre de archivo (con extensión) de una ruta local o una URL."""
    parsed = urlparse(path_or_url)
    if parsed.scheme in ("http", "https"):
        return os.path.basename(parsed.path)
    return os.path.basename(path_or_url)

def download_image(url: str) -> bytes:
    """Descarga la imagen desde la URL y devuelve los bytes."""
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.content

def read_local_file(path: str) -> bytes:
    """Lee un fichero local y devuelve su contenido en bytes."""
    with open(path, "rb") as f:
        return f.read()

def upload_media(file_bytes: bytes, filename: str) -> dict:
    """
    Hace POST a /wp-json/wp/v2/media
    Body = binary file, con header Content-Disposition: attachment; filename="filename"
    """
    url = f"{WP_URL.rstrip('/')}/wp-json/wp/v2/media"
    headers = HEADERS.copy()
    headers.update({
        "Content-Disposition": f'attachment; filename="{filename}"',
        # O bien el mimeType correcto: "image/png", "image/jpeg"
        "Content-Type": "application/octet-stream"
    })
    resp = requests.post(url, data=file_bytes, headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser(
        description="Sube una imagen a WordPress Media Library"
    )
    parser.add_argument(
        "source",
        help="Ruta local de la imagen o URL remota (http://.../imagen.png)"
    )
    args = parser.parse_args()

    src = args.source
    print(f"🖼️  Preparando subida de: {src}")
    filename = get_filename_from_path_or_url(src)
    print(f"📛 Nombre de archivo: {filename}")

    try:
        if src.startswith(("http://", "https://")):
            data = download_image(src)
        else:
            data = read_local_file(src)
    except Exception as e:
        print(f"❌ Error al obtener bytes de la imagen: {e}")
        sys.exit(1)

    try:
        result = upload_media(data, filename)
    except Exception as e:
        print(f"❌ Error al subir media a WordPress: {e}")
        if hasattr(e, "response"):
            print(e.response.text)
        sys.exit(1)

    media_id = result.get("id")
    media_url = result.get("source_url")
    print("✅ Subida correcta!")
    print(f"   • ID: {media_id}")
    print(f"   • URL: {media_url}")

if __name__ == "__main__":
    main()
