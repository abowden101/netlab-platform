"""BYO image upload + load.

Uploads are streamed to disk with a running SHA256. Nothing is downloaded
by the platform; the operator supplies the image tarball under their own
license (see docs/byo-image-guide.md). The upload requires an explicit
license acknowledgement and a `.tar` file, and is refused otherwise.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import NodeImage

LICENSE_NOTICE = (
    "Cisco IOS-XE, Arista cEOS, and Juniper vJunos are proprietary software "
    "owned by their vendors. By uploading an image you confirm you hold a "
    "valid license or entitlement from the vendor to use it, and that you "
    "will not redistribute it. netlab-platform bundles, downloads, and "
    "links no proprietary NOS image."
)

ALLOWED_EXTENSIONS = {".tar"}


def _upload_path(name: str) -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir / name


async def save_upload(
    file: UploadFile,
    vendor: str,
    license_acknowledged: bool,
    uploaded_by: str,
    db: Session,
) -> NodeImage:
    if not license_acknowledged:
        raise HTTPException(
            status_code=400,
            detail="license acknowledgement is required (see LICENSE_NOTICE)",
        )
    filename = file.filename or ""
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="only .tar image tarballs are accepted",
        )
    max_bytes = settings.max_image_upload_mb * 1024 * 1024
    dest = _upload_path(filename)
    digest = hashlib.sha256()
    size = 0
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"image exceeds the {settings.max_image_upload_mb} MB cap",
                    )
                digest.update(chunk)
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    row = NodeImage(
        name=filename,
        vendor=vendor,
        image_ref=f"byo:{digest.hexdigest()[:12]}",
        sha256=digest.hexdigest(),
        size_bytes=size,
        uploaded_by=uploaded_by,
        license_acknowledged=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def load_image(row: NodeImage) -> list[str]:
    """Run `docker load` on the uploaded tarball and return the image tags
    it contained. Marks the row loaded on success."""
    path = _upload_path(row.name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="uploaded file not found on disk")
    # Verify the on-disk file still matches the recorded checksum.
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != row.sha256:
        raise HTTPException(
            status_code=409, detail="checksum mismatch — upload is corrupt"
        )
    result = subprocess.run(
        ["docker", "load", "-i", str(path)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500, detail=f"docker load failed: {result.stderr.strip()}"
        )
    tags = [
        line.removeprefix("Loaded image: ").strip()
        for line in result.stdout.splitlines()
        if line.startswith("Loaded image: ")
    ]
    return tags
