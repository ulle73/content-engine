"""Bundle tracked application and upstream source, excluding secrets and runtime data."""

import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent.parent
destination = root / "data" / "source.zip"
destination.parent.mkdir(exist_ok=True)
with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
    for repo in [root, root / "vendor/brightbean-studio", root / "vendor/social-media-skills"]:
        paths = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().split("\0")
        for name in paths:
            path = repo / name
            if name and path.is_file() and ".env" not in path.name.replace(".env.example", ""):
                archive.write(path, path.relative_to(root))
print("Source archive created; only version-controlled files included.")
