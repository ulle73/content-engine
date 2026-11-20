"""Ladda upp färdiga filer till Google Drive utan att filen passerar n8n.

Flöde (Google Drive resumable upload):
  1. POST liten JSON till ett n8n-flöde, som äger Google-inloggningen och svarar med en upload_url
     (sessions-URL, giltig ca en vecka):
       - "CE – Uppladdning till Drive (Claude)" (content-engine-drive-session): {mapp, namn, mime, storlek}, valfri mapp.
       - "CE – Publicera till CONTENT" (content-engine-publicera): {namn, storlek}. Mappen är fast
         (CONTENT/01 Publicerat) och ett mapp-id i anropet ignoreras. Används av Godkänn i dashboarden.
  2. Filen PUT:as strömmande direkt till upload_url. Ingen OAuth-token behövs för det steget
     (https://developers.google.com/workspace/drive/api/guides/manage-uploads#resumable).
     En avbruten uppladdning fortsätter från rätt byte med samma upload_url (status()).

Därför hamnar inga filbytes i n8n eller i PostgreSQL-tabellen binary_data.
Bakgrund: 2026-11-05 lämnade 62 videor via den gamla multipart-webhooken kvar 519 MB i binary_data.

Användning:
  python scripts/drive_upload.py <drive-mapp-id> <fil> [<fil> ...]

Kräver i .env: GK_DRIVE_UPLOAD_SECRET och GK_DRIVE_UPLOAD_URL (n8n-bas eller gammal webhook-URL;
sökvägen byts automatiskt). Flödet måste vara publicerat i n8n.
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
PUBLICERA_PATH = "/webhook/content-engine-publicera"
PAPPERSKORG_PATH = "/webhook/content-engine-papperskorg"
CHUNK = 1024 * 1024
UPLOAD_PREFIX = "https://www.googleapis.com/upload/drive/"


class DriveFel(Exception):
    """Ett fel från n8n eller Google, med en text som går att visa."""

    def __init__(self, text: str, *, sessionen_slut: bool = False):
        super().__init__(text)
        self.sessionen_slut = sessionen_slut


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


def n8n_url(path: str = SESSION_PATH) -> str:
    raw = os.environ.get("GK_DRIVE_SESSION_URL") or os.environ.get("GK_DRIVE_UPLOAD_URL") or ""
    if not raw:
        raise DriveFel("GK_DRIVE_UPLOAD_URL saknas.")
    parts = urllib.parse.urlsplit(raw)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def session_url() -> str:
    return n8n_url(SESSION_PATH)


def _post_json(url: str, secret: str, body: dict, namn: str) -> str:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-gk-drive": secret},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise DriveFel(f"n8n svarade {exc.code} för {namn}.") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise DriveFel(f"n8n kunde inte nås för {namn} ({type(exc).__name__}).") from None
    upload_url = str(data.get("upload_url", ""))
    if not upload_url.startswith(UPLOAD_PREFIX):
        raise DriveFel(f"n8n gav ingen giltig upload_url för {namn}.")
    return upload_url


def request_session(url: str, secret: str, folder: str, path: Path, size: int, mime: str) -> str:
    """Valfri mapp (Claudes verktyg)."""
    return _post_json(url, secret, {"mapp": folder, "namn": path.name, "mime": mime, "storlek": size}, path.name)


def publicera_session(namn: str, size: int) -> str:
    """Sessions-URL för en fil i CONTENT/01 Publicerat. Mappen är fast i n8n-flödet; vi skickar bara namn och storlek."""
    secret = os.environ.get("GK_DRIVE_UPLOAD_SECRET", "")
    if not secret:
        raise DriveFel("GK_DRIVE_UPLOAD_SECRET saknas.")
    return _post_json(n8n_url(PUBLICERA_PATH), secret, {"namn": namn, "storlek": size}, namn)


def papperskorg(drive_id: str) -> str:
    """Put one file in Drive's trash through "CE – Papperskorg i CONTENT". Only files in CONTENT/01 Publicerat are
    touched (the flow checks the parent folder). Returns 'papperskorg', 'redan_i_papperskorgen' or 'saknas'."""
    secret = os.environ.get("GK_DRIVE_UPLOAD_SECRET", "")
    if not secret:
        raise DriveFel("GK_DRIVE_UPLOAD_SECRET saknas.")
    req = urllib.request.Request(
        n8n_url(PAPPERSKORG_PATH), data=json.dumps({"drive_id": drive_id}).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-gk-drive": secret},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise DriveFel(f"Drive-filen kunde inte läggas i papperskorgen (n8n svarade {exc.code}).") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise DriveFel(f"n8n kunde inte nås ({type(exc).__name__}).") from None
    resultat = str(data.get("resultat", ""))
    if not data.get("ok") or resultat not in {"papperskorg", "redan_i_papperskorgen", "saknas"}:
        raise DriveFel("Drive bekräftade inte att filen lades i papperskorgen.")
    return resultat


def status(upload_url: str, size: int) -> dict | int:
    """Var en påbörjad uppladdning står: filens metadata om den är klar, annars nästa byte att skicka."""
    req = urllib.request.Request(upload_url, data=b"", method="PUT",
                                 headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 308:
            rng = exc.headers.get("Range") or ""
            return int(rng.rsplit("-", 1)[1]) + 1 if rng.startswith("bytes=") else 0
        if exc.code in (404, 410):
            raise DriveFel("Uppladdningssessionen har gått ut.", sessionen_slut=True) from None
        raise DriveFel(f"Google svarade {exc.code} på statusfrågan.") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise DriveFel(f"Google kunde inte nås ({type(exc).__name__}).") from None


def put_stream(upload_url: str, stream, size: int, mime: str, *, offset: int = 0) -> dict:
    """Strömmar filen (från offset) till upload_url utan att hela filen ligger i minnet. Ger filens metadata."""
    hoppa = offset
    while hoppa:
        bit = stream.read(min(CHUNK, hoppa))
        if not bit:
            raise DriveFel("Filen är kortare än väntat.")
        hoppa -= len(bit)
    headers = {"Content-Length": str(size - offset), "Content-Type": mime}
    if offset:
        headers["Content-Range"] = f"bytes {offset}-{size - 1}/{size}"
    req = urllib.request.Request(upload_url, data=iter(lambda: stream.read(CHUNK), b""), method="PUT", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            raise DriveFel("Uppladdningssessionen har gått ut.", sessionen_slut=True) from None
        raise DriveFel(f"Google svarade {exc.code} på uppladdningen.") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise DriveFel(f"Uppladdningen avbröts ({type(exc).__name__}).") from None


def put_file(upload_url: str, path: Path, size: int, mime: str) -> dict:
    with path.open("rb") as fh:
        return put_stream(upload_url, fh, size, mime)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    load_env()
    secret = os.environ.get("GK_DRIVE_UPLOAD_SECRET", "")
    if not secret:
        sys.exit("GK_DRIVE_UPLOAD_SECRET saknas i .env")
    folder, files = argv[1], [Path(p) for p in argv[2:]]
    try:
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
            print(f"{path.name}\thttps://drive.google.com/file/d/{meta.get('id', '')}/view")
    except DriveFel as exc:
        sys.exit(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
