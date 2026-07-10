import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..db import connect, fetch_all, fetch_one
from ..services.blockchain import chain_client
from ..services.cleanup import delete_files_by_ids
from ..services.storage import save_upload

router = APIRouter(prefix="/api/training-tasks", tags=["training-tasks"])


@router.get("")
def list_training_tasks(project_id: int | None = None):
    if project_id:
        return fetch_all("SELECT * FROM training_tasks WHERE project_id = ? ORDER BY id DESC", (project_id,))
    return fetch_all("SELECT * FROM training_tasks ORDER BY id DESC")


@router.post("")
async def create_training_task(
    project_id: int = Form(...),
    name: str = Form(...),
    dataset_ids: str = Form(...),
    algorithm: str = Form(...),
    description: str = Form(""),
    code_file: UploadFile = File(...),
    config_file: UploadFile = File(...),
):
    if not fetch_one("SELECT id FROM projects WHERE id = ?", (project_id,)):
        raise HTTPException(status_code=404, detail="未找到项目")

    try:
        parsed_dataset_ids = json.loads(dataset_ids)
        if not isinstance(parsed_dataset_ids, list) or not parsed_dataset_ids:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="数据集 ID 列表必须是非空 JSON 数组") from exc

    for dataset_id in parsed_dataset_ids:
        if not fetch_one("SELECT id FROM datasets WHERE id = ?", (dataset_id,)):
            raise HTTPException(status_code=404, detail=f"未找到数据集 {dataset_id}")

    code = await save_upload(code_file, "code")
    config = await save_upload(config_file, "configs")
    payload = {
        "project_id": project_id,
        "name": name,
        "dataset_ids": parsed_dataset_ids,
        "algorithm": algorithm,
        "code_hash": code["sha256"],
        "config_hash": config["sha256"],
    }
    tx_hash = chain_client.register("TrainingTaskRegistered", payload)

    with connect() as conn:
        code_file_id = conn.execute(
            """
            INSERT INTO files (object_type, original_name, stored_path, sha256, size_bytes)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("code", code["original_name"], code["stored_path"], code["sha256"], code["size_bytes"]),
        ).lastrowid
        config_file_id = conn.execute(
            """
            INSERT INTO files (object_type, original_name, stored_path, sha256, size_bytes)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("config", config["original_name"], config["stored_path"], config["sha256"], config["size_bytes"]),
        ).lastrowid
        task_id = conn.execute(
            """
            INSERT INTO training_tasks
              (project_id, name, dataset_ids, algorithm, description, code_file_id, config_file_id, code_hash, config_hash, tx_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                name,
                json.dumps(parsed_dataset_ids),
                algorithm,
                description,
                code_file_id,
                config_file_id,
                code["sha256"],
                config["sha256"],
                tx_hash,
            ),
        ).lastrowid

    return fetch_one("SELECT * FROM training_tasks WHERE id = ?", (task_id,))


@router.delete("/{task_id}")
def delete_training_task(task_id: int):
    task = fetch_one("SELECT * FROM training_tasks WHERE id = ?", (task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="未找到训练任务")

    models = fetch_all("SELECT id, model_file_id FROM model_versions WHERE training_task_id = ?", (task_id,))
    model_ids = [row["id"] for row in models]
    file_ids = [task["code_file_id"], task["config_file_id"]]
    file_ids.extend(row["model_file_id"] for row in models)

    with connect() as conn:
        if model_ids:
            placeholders = ",".join("?" for _ in model_ids)
            conn.execute(f"DELETE FROM audit_records WHERE model_version_id IN ({placeholders})", model_ids)
        conn.execute("DELETE FROM model_versions WHERE training_task_id = ?", (task_id,))
        conn.execute("DELETE FROM training_rounds WHERE training_task_id = ?", (task_id,))
        conn.execute("DELETE FROM training_tasks WHERE id = ?", (task_id,))

    delete_files_by_ids(file_ids)
    return {"status": "已删除", "training_task_id": task_id}
