"""BYO image routes: list, upload (license acknowledgement required),
load (docker load on the lab host), delete."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.roles import require_instructor
from app.core.deps import get_db
from app.db.models import NodeImage, User
from app.images.upload import LICENSE_NOTICE, load_image, save_upload

router = APIRouter()


@router.get("")
def list_images(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = db.query(NodeImage).order_by(NodeImage.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "vendor": r.vendor,
            "image_ref": r.image_ref,
            "sha256": r.sha256,
            "size_bytes": r.size_bytes,
            "uploaded_by": r.uploaded_by,
            "license_acknowledged": r.license_acknowledged,
            "loaded": r.loaded,
        }
        for r in rows
    ]


@router.post("/upload", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    vendor: str = Form(...),
    license_acknowledged: bool = Form(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = await save_upload(file, vendor, license_acknowledged, user.email, db)
    return {
        "id": row.id,
        "name": row.name,
        "vendor": row.vendor,
        "image_ref": row.image_ref,
        "sha256": row.sha256,
        "size_bytes": row.size_bytes,
        "license_notice": LICENSE_NOTICE,
    }


@router.post("/{image_id}/load")
def load_uploaded_image(
    image_id: int,
    user: User = Depends(require_instructor),
    db: Session = Depends(get_db),
):
    row = db.get(NodeImage, image_id)
    if row is None:
        raise HTTPException(status_code=404, detail="image not found")
    tags = load_image(row)
    row.loaded = True
    db.commit()
    return {"id": row.id, "loaded": True, "tags": tags}


@router.delete("/{image_id}")
def delete_image(
    image_id: int,
    user: User = Depends(require_instructor),
    db: Session = Depends(get_db),
):
    row = db.get(NodeImage, image_id)
    if row is None:
        raise HTTPException(status_code=404, detail="image not found")
    db.delete(row)
    db.commit()
    return {"deleted": image_id}
