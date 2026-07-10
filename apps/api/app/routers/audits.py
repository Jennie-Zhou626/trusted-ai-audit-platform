import json

from fastapi import APIRouter, Form, HTTPException

from ..db import connect, fetch_all, fetch_one
from ..services.blockchain import chain_client
from ..utils.hashing import sha256_file

router = APIRouter(prefix="/api/audits", tags=["audits"])


def check_file(file_id: int, expected_hash: str, label: str) -> dict:
    file_row = fetch_one("SELECT * FROM files WHERE id = ?", (file_id,))
    if not file_row:
        return {"item": label, "expected": expected_hash, "actual": "", "passed": False, "message": "文件缺失"}
    actual = sha256_file(file_row["stored_path"])
    return {
        "item": label,
        "expected": expected_hash,
        "actual": actual,
        "passed": actual == expected_hash,
        "message": "一致" if actual == expected_hash else "哈希不一致",
    }


def build_audit_checks(model: dict, task: dict) -> list[dict]:
    checks = [
        check_file(model["model_file_id"], model["model_hash"], "模型文件哈希"),
        check_file(task["code_file_id"], task["code_hash"], "训练代码哈希"),
        check_file(task["config_file_id"], task["config_hash"], "参数配置哈希"),
    ]

    for dataset_id in json.loads(task["dataset_ids"]):
        dataset = fetch_one("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
        if dataset:
            checks.append(check_file(dataset["file_id"], dataset["dataset_hash"], f"数据集 #{dataset_id} 哈希"))
            checks.append(
                {
                    "item": f"数据集 #{dataset_id} 授权规则",
                    "expected": "存在授权类型",
                    "actual": dataset["license_type"],
                    "passed": bool(dataset["license_type"]),
                    "message": "已登记" if dataset["license_type"] else "缺少授权类型",
                }
            )
        else:
            checks.append(
                {
                    "item": f"数据集 #{dataset_id}",
                    "expected": "已登记数据集",
                    "actual": "缺失",
                    "passed": False,
                    "message": "数据集缺失",
                }
            )

    return checks


@router.get("")
def list_audits(project_id: int | None = None):
    if project_id:
        return fetch_all("SELECT * FROM audit_records WHERE project_id = ? ORDER BY id DESC", (project_id,))
    return fetch_all("SELECT * FROM audit_records ORDER BY id DESC")


@router.get("/report/{model_version_id}")
def get_audit_report(model_version_id: int):
    model = fetch_one("SELECT * FROM model_versions WHERE id = ?", (model_version_id,))
    if not model:
        raise HTTPException(status_code=404, detail="未找到模型版本")
    task = fetch_one("SELECT * FROM training_tasks WHERE id = ?", (model["training_task_id"],))
    if not task:
        raise HTTPException(status_code=404, detail="未找到训练任务")

    dataset_ids = json.loads(task["dataset_ids"])
    datasets = []
    missing_datasets = []
    for dataset_id in dataset_ids:
        dataset = fetch_one("SELECT * FROM datasets WHERE id = ?", (dataset_id,))
        if dataset:
            datasets.append(dataset)
        else:
            missing_datasets.append(dataset_id)

    rounds = fetch_all(
        "SELECT * FROM training_rounds WHERE training_task_id = ? ORDER BY round_index ASC, id ASC",
        (task["id"],),
    )
    audits = fetch_all("SELECT * FROM audit_records WHERE model_version_id = ? ORDER BY id DESC", (model_version_id,))
    latest_audit = audits[0] if audits else None
    latest_checks = json.loads(latest_audit["checks"]) if latest_audit else []
    failed_checks = [item for item in latest_checks if not item.get("passed")]

    score = 100
    warnings = []
    strengths = []

    if not datasets:
        score -= 25
        warnings.append("该训练任务没有关联已登记的数据集。")
    else:
        strengths.append(f"训练任务已关联 {len(datasets)} 个已登记数据集。")
    if missing_datasets:
        score -= 20
        warnings.append(f"存在缺失的数据集引用 ID：{missing_datasets}。")
    if not rounds:
        score -= 15
        warnings.append("尚未登记协同训练轮次记录。")
    else:
        strengths.append(f"已记录 {len(rounds)} 条协同训练轮次存证。")
    if not latest_audit:
        score -= 20
        warnings.append("该模型版本尚未生成审计记录。")
    elif latest_audit["result"] != "passed":
        score -= min(40, 10 + len(failed_checks) * 8)
        warnings.append("最新审计结果为失败，请复核哈希不一致或材料缺失项。")
    else:
        strengths.append("最新审计结果为通过。")
    if not model["tx_hash"] or not task["tx_hash"]:
        score -= 10
        warnings.append("部分关键对象缺少交易哈希。")
    else:
        strengths.append("模型版本和训练任务均包含交易哈希。")
    score = max(0, min(100, score))
    level = "high" if score >= 85 else "medium" if score >= 60 else "low"

    return {
        "model_version": model,
        "training_task": task,
        "datasets": datasets,
        "training_rounds": rounds,
        "latest_audit": latest_audit,
        "latest_checks": latest_checks,
        "score": score,
        "trust_level": level,
        "strengths": strengths,
        "warnings": warnings,
        "recommendations": [
            "原始数据和模型文件继续保存在链下，链上仅记录哈希和关键元数据。",
            "将重要协同训练轮次登记为异步审计检查点，提升过程可追溯性。",
            "若从课堂演示扩展到真实场景，建议部署到联盟链或以太坊兼容测试链。",
        ],
    }


@router.post("")
def create_audit(model_version_id: int = Form(...), reason: str = Form("自动审计")):
    model = fetch_one("SELECT * FROM model_versions WHERE id = ?", (model_version_id,))
    if not model:
        raise HTTPException(status_code=404, detail="未找到模型版本")
    task = fetch_one("SELECT * FROM training_tasks WHERE id = ?", (model["training_task_id"],))
    if not task:
        raise HTTPException(status_code=404, detail="未找到训练任务")

    checks = build_audit_checks(model, task)
    result = "passed" if all(item["passed"] for item in checks) else "failed"
    payload = {"model_version_id": model_version_id, "result": result, "checks": checks}
    tx_hash = chain_client.register("AuditRecordRegistered", payload)

    with connect() as conn:
        audit_id = conn.execute(
            """
            INSERT INTO audit_records (project_id, model_version_id, result, reason, checks, tx_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (model["project_id"], model_version_id, result, reason, json.dumps(checks, ensure_ascii=False), tx_hash),
        ).lastrowid

    return fetch_one("SELECT * FROM audit_records WHERE id = ?", (audit_id,))


@router.delete("/{audit_id}")
def delete_audit(audit_id: int):
    if not fetch_one("SELECT id FROM audit_records WHERE id = ?", (audit_id,)):
        raise HTTPException(status_code=404, detail="未找到审计记录")

    with connect() as conn:
        conn.execute("DELETE FROM audit_records WHERE id = ?", (audit_id,))
    return {"status": "已删除", "audit_id": audit_id}
