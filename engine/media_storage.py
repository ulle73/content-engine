"""Two small file stores. PostgreSQL contains metadata only; buckets remain private."""

import os
from contextlib import contextmanager
from pathlib import PurePosixPath
from tempfile import SpooledTemporaryFile
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings


class MediaError(Exception):
    pass


def local_path(key):
    if PurePosixPath(key).is_absolute() or ".." in PurePosixPath(key).parts or "\\" in key:
        raise MediaError("Ogiltig filsökväg.")
    root = settings.MEDIA_ROOT.resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise MediaError("Ogiltig filsökväg.")
    return path


def r2():
    names = ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
    endpoint = os.environ.get("R2_ENDPOINT_URL") or (f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com" if os.environ.get("R2_ACCOUNT_ID") else "")
    parsed = urlparse(endpoint)
    if not all(os.environ.get(k) for k in names) or not endpoint:
        raise MediaError("R2 är inte konfigurerat. Driftansvarig behöver lägga in R2-inställningarna.")
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".r2.cloudflarestorage.com") or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.path not in ("", "/"):
        raise MediaError("R2_ENDPOINT_URL ska vara bucketens HTTPS-endpoint för S3 API.")
    return boto3.client(
        "s3", endpoint_url=endpoint.rstrip("/"),
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("R2_REGION", "auto"), config=Config(signature_version="s3v4", connect_timeout=10, read_timeout=90,
                                        retries={"max_attempts": 2}, request_checksum_calculation="when_required"),
    )


def check_storage(backend=None):
    backend = backend or settings.MEDIA_STORAGE
    if backend not in {"local", "r2"} or (backend == "local" and not settings.LOCAL_HTTP):
        raise MediaError("Publik drift behöver R2-lagring.")
    if backend == "r2":
        r2()
    return backend


def put(key, data, mime, backend=None):
    backend = check_storage(backend)
    try:
        if backend == "local":
            path = local_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        else:
            r2().put_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=key, Body=data, ContentType=mime)
    except (OSError, BotoCoreError, ClientError) as exc:
        raise MediaError("Filen kunde inte sparas. Kontrollera lagringen och försök igen.") from exc
    return backend


@contextmanager
def open_asset(asset):
    try:
        if asset.storage_backend == "local":
            with local_path(asset.storage_key).open("rb") as file:
                yield file
        else:
            with SpooledTemporaryFile(max_size=8 * 1024 * 1024) as file:
                r2().download_fileobj(os.environ["R2_BUCKET_NAME"], asset.storage_key, file)
                file.seek(0)
                yield file
    except (OSError, BotoCoreError, ClientError) as exc:
        raise MediaError("Den sparade filen kunde inte läsas.") from exc


def download_url(asset):
    try:
        return r2().generate_presigned_url("get_object", Params={"Bucket": os.environ["R2_BUCKET_NAME"],
                                              "Key": asset.storage_key}, ExpiresIn=3600)
    except (BotoCoreError, ClientError) as exc:
        raise MediaError("Förhandsvisningen kunde inte öppnas.") from exc


def delete_file(asset):
    try:
        if asset.storage_backend == "local":
            local_path(asset.storage_key).unlink(missing_ok=True)
        else:
            r2().delete_object(Bucket=os.environ["R2_BUCKET_NAME"], Key=asset.storage_key)
    except (OSError, BotoCoreError, ClientError) as exc:
        raise MediaError("Filen kunde inte tas bort. Försök igen.") from exc
