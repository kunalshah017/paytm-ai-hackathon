import uuid

import httpx
from fastapi import APIRouter, UploadFile, HTTPException

from app.config import settings

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/image/")
async def upload_image(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP, and GIF images are allowed")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File size must be under 5MB")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    storage_path = f"inventory/{filename}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.supabase_url}/storage/v1/object/product-images/{storage_path}",
            headers={
                "Authorization": f"Bearer {settings.supabase_service_key}",
                "Content-Type": file.content_type or "application/octet-stream",
            },
            content=content,
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Failed to upload image to storage")

    public_url = f"{settings.supabase_url}/storage/v1/object/public/product-images/{storage_path}"
    return {"url": public_url}
