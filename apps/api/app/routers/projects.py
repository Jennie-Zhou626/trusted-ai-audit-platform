from fastapi import APIRouter, Form, HTTPException

from ..db import connect, fetch_all, fetch_one
from ..services.cleanup import delete_files_by_ids

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
def list_projects():
    return fetch_all("SELECT * FROM projects ORDER BY id DESC")


@router.post("")
def create_project(name: str = Form(...), description: str = Form("")):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description),
        )
        project_id = cur.lastrowid
    return fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))


@router.delete("/{project_id}")
def delete_project(project_id: int):
    if not fetch_one("SELECT id FROM projects WHERE id = ?", (project_id,)):
        raise HTTPException(status_code=404, detail="未找到项目")

    datasets = fetch_all("SELECT file_id FROM datasets WHERE project_id = ?", (project_id,))
    tasks = fetch_all("SELECT code_file_id, config_file_id FROM training_tasks WHERE project_id = ?", (project_id,))
    models = fetch_all("SELECT model_file_id FROM model_versions WHERE project_id = ?", (project_id,))
    file_ids = [row["file_id"] for row in datasets]
    file_ids.extend(row["code_file_id"] for row in tasks)
    file_ids.extend(row["config_file_id"] for row in tasks)
    file_ids.extend(row["model_file_id"] for row in models)

    with connect() as conn:
        conn.execute("DELETE FROM audit_records WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM model_versions WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM training_tasks WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM datasets WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    delete_files_by_ids(file_ids)
    return {"status": "已删除", "project_id": project_id}
