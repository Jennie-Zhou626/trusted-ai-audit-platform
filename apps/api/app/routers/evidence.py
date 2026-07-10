import json

from fastapi import APIRouter, HTTPException

from ..db import fetch_all, fetch_one

router = APIRouter(prefix="/api/evidence-chain", tags=["evidence-chain"])


@router.get("/{model_version_id}")
def get_evidence_chain(model_version_id: int):
    model = fetch_one("SELECT * FROM model_versions WHERE id = ?", (model_version_id,))
    if not model:
        raise HTTPException(status_code=404, detail="未找到模型版本")

    task = fetch_one("SELECT * FROM training_tasks WHERE id = ?", (model["training_task_id"],))
    datasets = []
    if task:
        for dataset_id in json.loads(task["dataset_ids"]):
            dataset = fetch_one("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
            if dataset:
                datasets.append(dataset)
    rounds = []
    if task:
        rounds = fetch_all(
            "SELECT * FROM training_rounds WHERE training_task_id = ? ORDER BY round_index ASC, id ASC",
            (task["id"],),
        )

    audits = fetch_all("SELECT * FROM audit_records WHERE model_version_id = ? ORDER BY id DESC", (model_version_id,))
    return {
        "datasets": datasets,
        "training_task": task,
        "training_rounds": rounds,
        "model_version": model,
        "audits": audits,
    }
