"""Ladda upp färdiga filer till en Google Drive-mapp utan att filen passerar n8n.

Flöde (Google Drive resumable upload):
  1. POST liten JSON {mapp, namn, mime, storlek} till n8n-webhooken
     "CE – Uppladdning till Drive (Claude)" (sökväg content-engine-drive-session).
     n8n äger Google-inloggningen och svarar med en upload_url (sessions-URL, giltig ca en vecka).
  2. Filen PUT:as strömmande direkt till upload_url. Ingen OAuth-token behövs för det steget
     (https://developers.google.com/workspace/drive/api/guides/manage-uploads#resumable).

Därför hamnar inga filbytes i n8n eller i PostgreSQL-tabellen binary_data.
Bakgrund: 2026-11-05 lämnade 62 videor via den gamla multipart-webhooken kvar 519 MB i binary_data.

Användning:
  python scripts/drive_upload.py <drive-mapp-id> <fil> [<fil> ...]

Kräver i .env: GK_DRIVE_UPLOAD_SECRET och GK_DRIVE_UPLOAD_URL (n8n-bas eller gammal webhook-URL;
sökvägen byts automatiskt till content-engine-drive-session). Flödet måste vara publicerat i n8n.
Filerna laddas upp en i taget (ingen parallellitet), högst 2 GiB per fil.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024 * 1024
SESSION_PATH = "/webhook/content-engine-drive-session"
CHUNK = 1024 * 1024


def load_env() -> None:
    env = Path(__file__).resolve().parents[1] / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def session_url() -> str:
    raw = os.environ.get("GK_DRIVE_SESSION_URL") or os.environ.get("GK_DRIVE_UPLOAD_URL") or ""
    if not raw:
        sys.exit("GK_DRIVE_UPLOAD_URL saknas i .env")
    parts = urllib.parse.urlsplit(raw)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, SESSION_PATH, "", ""))


def request_session(url: str, secret: str, folder: str, path: Path, size: int, mime: str) -> str:
    body = json.dumps({"mapp": folder, "namn": path.name, "mime": mime, "storlek": size}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "x-gk-drive": secret},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:300].decode("utf-8", "replace")
        sys.exit(f"n8n svarade {exc.code} för {path.name}: {detail}")
    upload_url = data.get("upload_url", "")
    if not upload_url.startswith("https://www.googleapis.com/upload/drive/"):
        sys.exit(f"n8n gav ingen giltig upload_url för {path.name}")
    return upload_url


def put_file(upload_url: str, path: Path, size: int, mime: str) -> dict:
    with path.open("rb") as fh:
        req = urllib.request.Request(
            upload_url, data=iter(lambda: fh.read(CHUNK), b""), method="PUT",
            headers={"Content-Length": str(size), "Content-Type": mime},
        )
        try:
            with urllib.request.urlopen(req, timeout=900) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:300].decode("utf-8", "replace")
            sys.exit(f"Google svarade {exc.code} för {path.name}: {detail}")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    load_env()
    secret = os.environ.get("GK_DRIVE_UPLOAD_SECRET", "")
    if not secret:
        sys.exit("GK_DRIVE_UPLOAD_SECRET saknas i .env")
    folder, files = argv[1], [Path(p) for p in argv[2:]]
    url = session_url()
    for path in files:
        if not path.is_file():
            sys.exit(f"Filen finns inte: {path}")
        size = path.stat().st_size
        if size < 1 or size > MAX_BYTES:
            sys.exit(f"{path.name}: storleken {size} byte är utanför 1 byte–2 GiB")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        upload_url = request_session(url, secret, folder, path, size, mime)
        meta = put_file(upload_url, path, size, mime)
        file_id = meta.get("id", "")
        print(f"{path.name}\thttps://drive.google.com/file/d/{file_id}/view")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
