from fastapi import APIRouter, Form, HTTPException

from ..db import connect, fetch_all, fetch_one
from ..services.blockchain import chain_client
from ..utils.hashing import sha256_text

router = APIRouter(prefix="/api/training-rounds", tags=["training-rounds"])


@router.get("")
def list_training_rounds(training_task_id: int | None = None, project_id: int | None = None):
    if training_task_id:
        return fetch_all(
            "SELECT * FROM training_rounds WHERE training_task_id = ? ORDER BY round_index ASC, id ASC",
            (training_task_id,),
        )
    if project_id:
        return fetch_all(
            "SELECT * FROM training_rounds WHERE project_id = ? ORDER BY training_task_id DESC, round_index ASC",
            (project_id,),
        )
    return fetch_all("SELECT * FROM training_rounds ORDER BY id DESC")


@router.post("")
def create_training_round(
    project_id: int = Form(...),
    training_task_id: int = Form(...),
    round_index: int = Form(...),
    organization: str = Form(...),
    local_epochs: int = Form(1),
    sample_count: int = Form(0),
    gradient_hash: str = Form(""),
    checkpoint_uri: str = Form(""),
    privacy_method: str = Form("hash-only"),
):
    task = fetch_one("SELECT * FROM training_tasks WHERE id = ?", (training_task_id,))
    if not task:
        raise HTTPException(status_code=404, detail="未找到训练任务")
    if task["project_id"] != project_id:
        raise HTTPException(status_code=400, detail="训练任务不属于当前项目")
    if round_index < 1:
        raise HTTPException(status_code=400, detail="轮次必须为正整数")

    if not gradient_hash:
        gradient_hash = sha256_text(
            f"{project_id}|{training_task_id}|{round_index}|{organization}|{local_epochs}|{sample_count}|{checkpoint_uri}|{privacy_method}"
        )

    payload = {
        "project_id": project_id,
        "training_task_id": training_task_id,
        "round_index": round_index,
        "organization": organization,
        "gradient_hash": gradient_hash,
        "checkpoint_uri": checkpoint_uri,
        "privacy_method": privacy_method,
    }
    tx_hash = chain_client.register("TrainingRoundCommitted", payload)

    with connect() as conn:
        round_id = conn.execute(
            """
            INSERT INTO training_rounds
              (project_id, training_task_id, round_index, organization, local_epochs, sample_count,
               gradient_hash, checkpoint_uri, privacy_method, tx_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                training_task_id,
                round_index,
                organization,
                local_epochs,
                sample_count,
                gradient_hash,
                checkpoint_uri,
                privacy_method,
                tx_hash,
            ),
        ).lastrowid

    return fetch_one("SELECT * FROM training_rounds WHERE id = ?", (round_id,))


@router.delete("/{round_id}")
def delete_training_round(round_id: int):
    if not fetch_one("SELECT id FROM training_rounds WHERE id = ?", (round_id,)):
        raise HTTPException(status_code=404, detail="未找到协同训练轮次")

    with connect() as conn:
        conn.execute("DELETE FROM training_rounds WHERE id = ?", (round_id,))
    return {"status": "已删除", "training_round_id": round_id}
