from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..db import connect, fetch_all, fetch_one
from ..services.blockchain import chain_client
from ..services.cleanup import delete_files_by_ids
from ..services.storage import save_upload

router = APIRouter(prefix="/api/model-versions", tags=["model-versions"])


@router.get("")
def list_model_versions(project_id: int | None = None):
    if project_id:
        return fetch_all("SELECT * FROM model_versions WHERE project_id = ? ORDER BY id DESC", (project_id,))
    return fetch_all("SELECT * FROM model_versions ORDER BY id DESC")


@router.post("")
async def create_model_version(
    project_id: int = Form(...),
    training_task_id: int = Form(...),
    name: str = Form(...),
    metrics: str = Form("{}"),
    model_file: UploadFile = File(...),
):
    task = fetch_one("SELECT * FROM training_tasks WHERE id = ?", (training_task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="未找到训练任务")
    if task["project_id"] != project_id:
        raise HTTPException(status_code=400, detail="训练任务不属于当前项目")

    model = await save_upload(model_file, "models")
    payload = {
        "project_id": project_id,
        "training_task_id": training_task_id,
        "name": name,
        "model_hash": model["sha256"],
        "metrics": metrics,
    }
    tx_hash = chain_client.register("ModelVersionRegistered", payload)

    with connect() as conn:
        model_file_id = conn.execute(
            """
            INSERT INTO files (object_type, original_name, stored_path, sha256, size_bytes)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("model", model["original_name"], model["stored_path"], model["sha256"], model["size_bytes"]),
        ).lastrowid
        model_id = conn.execute(
            """
            INSERT INTO model_versions
              (project_id, training_task_id, name, model_file_id, metrics, model_hash, tx_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, training_task_id, name, model_file_id, metrics, model["sha256"], tx_hash),
        ).lastrowid

    return fetch_one("SELECT * FROM model_versions WHERE id = ?", (model_id,))


@router.delete("/{model_id}")
def delete_model_version(model_id: int):
    model = fetch_one("SELECT * FROM model_versions WHERE id = ?", (model_id,))
    if not model:
        raise HTTPException(status_code=404, detail="未找到模型版本")

    with connect() as conn:
        conn.execute("DELETE FROM audit_records WHERE model_version_id = ?", (model_id,))
        conn.execute("DELETE FROM model_versions WHERE id = ?", (model_id,))

    delete_files_by_ids([model["model_file_id"]])
    return {"status": "已删除", "model_version_id": model_id}
