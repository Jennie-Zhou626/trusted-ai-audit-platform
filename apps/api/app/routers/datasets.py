import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..db import connect, fetch_all, fetch_one
from ..services.blockchain import chain_client
from ..services.cleanup import delete_files_by_ids
from ..services.storage import save_upload

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("")
def list_datasets(project_id: int | None = None):
    if project_id:
        return fetch_all("SELECT * FROM datasets WHERE project_id = ? ORDER BY id DESC", (project_id,))
    return fetch_all("SELECT * FROM datasets ORDER BY id DESC")


@router.post("")
async def create_dataset(
    project_id: int = Form(...),
    name: str = Form(...),
    provider: str = Form(...),
    source: str = Form(""),
    license_type: str = Form(...),
    file: UploadFile = File(...),
):
    if not fetch_one("SELECT id FROM projects WHERE id = ?", (project_id,)):
        raise HTTPException(status_code=404, detail="未找到项目")

    saved = await save_upload(file, "datasets")
    payload = {
        "project_id": project_id,
        "name": name,
        "provider": provider,
        "source": source,
        "license_type": license_type,
        "dataset_hash": saved["sha256"],
    }
    tx_hash = chain_client.register("DatasetRegistered", payload)

    with connect() as conn:
        file_id = conn.execute(
            """
            INSERT INTO files (object_type, original_name, stored_path, sha256, size_bytes)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("dataset", saved["original_name"], saved["stored_path"], saved["sha256"], saved["size_bytes"]),
        ).lastrowid
        dataset_id = conn.execute(
            """
            INSERT INTO datasets
              (project_id, name, provider, source, license_type, file_id, dataset_hash, tx_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, name, provider, source, license_type, file_id, saved["sha256"], tx_hash),
        ).lastrowid

    return fetch_one("SELECT * FROM datasets WHERE id = ?", (dataset_id,))


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int):
    dataset = fetch_one("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
    if not dataset:
        raise HTTPException(status_code=404, detail="未找到数据集")

    tasks = fetch_all("SELECT id, dataset_ids FROM training_tasks")
    for task in tasks:
        try:
            ids = json.loads(task["dataset_ids"])
        except json.JSONDecodeError:
            ids = []
        if dataset_id in ids:
            raise HTTPException(
                status_code=400,
                detail=f"该数据集被训练任务 {task['id']} 引用，请先删除对应训练任务。",
            )

    with connect() as conn:
        conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
    delete_files_by_ids([dataset["file_id"]])
    return {"status": "已删除", "dataset_id": dataset_id}
