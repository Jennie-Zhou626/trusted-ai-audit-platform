from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from ..config import UPLOAD_DIR
from ..utils.hashing import sha256_file


async def save_upload(file: UploadFile, object_type: str) -> dict:
    suffix = Path(file.filename or "upload.bin").suffix
    target_dir = UPLOAD_DIR / object_type
    target_dir.mkdir(parents=True, exist_ok=True)
    stored = target_dir / f"{uuid4().hex}{suffix}"

    size = 0
    with stored.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            out.write(chunk)

    return {
        "original_name": file.filename or "upload.bin",
        "stored_path": str(stored),
        "sha256": sha256_file(stored),
        "size_bytes": size,
    }
