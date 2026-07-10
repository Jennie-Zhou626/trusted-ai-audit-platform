import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException

from ..config import ROOT_DIR, UPLOAD_DIR
from ..db import connect, fetch_one
from ..services.blockchain import chain_client
from ..services.cleanup import reset_all_runtime_data
from ..utils.hashing import sha256_file, sha256_text
from .audits import build_audit_checks

router = APIRouter(prefix="/api/samples", tags=["samples"])


def store_example_file(source: Path, object_type: str) -> int:
    target_dir = UPLOAD_DIR / object_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid4().hex}{source.suffix}"
    shutil.copyfile(source, target)
    digest = sha256_file(target)
    with connect() as conn:
        return conn.execute(
            """
            INSERT INTO files (object_type, original_name, stored_path, sha256, size_bytes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (object_type, source.name, str(target), digest, target.stat().st_size),
        ).lastrowid


def create_audit_record(model_version_id: int, reason: str) -> dict:
    model = fetch_one("SELECT * FROM model_versions WHERE id = ?", (model_version_id,))
    if not model:
        raise HTTPException(status_code=404, detail="未找到模型版本")

    task = fetch_one("SELECT * FROM training_tasks WHERE id = ?", (model["training_task_id"],))
    if not task:
        raise HTTPException(status_code=404, detail="未找到训练任务")

    checks = build_audit_checks(model, task)

    result = "passed" if all(item["passed"] for item in checks) else "failed"
    payload = {"project_id": model["project_id"], "model_version_id": model_version_id, "result": result}
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


@router.post("/seed-sample")
def seed_sample(reset: bool = Form(True)):
    if reset:
        reset_all_runtime_data()

    sample = ROOT_DIR / "examples" / "sample"
    required = [
        sample / "data" / "iris_org_a.csv",
        sample / "data" / "iris_org_b.csv",
        sample / "code" / "train_iris.py",
        sample / "config" / "iris_config.json",
        sample / "models" / "iris_model_v1.pkl",
        sample / "models" / "iris_model_v2.pkl",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise HTTPException(status_code=500, detail={"缺少样例文件": missing})

    with connect() as conn:
        project_id = conn.execute(
            """
            INSERT INTO projects (name, description)
            VALUES (?, ?)
            """,
            (
                "多机构 Iris 分类模型可信审计样例项目",
                "机构A与机构B共同提供训练数据，训练方登记模型版本，审计方验证训练过程证据链。",
            ),
        ).lastrowid
        organization_ids = [
            conn.execute(
                """
                INSERT INTO organizations (name, role, wallet_address, contact)
                VALUES (?, ?, ?, ?)
                """,
                ("机构A 数据治理中心", "data_provider", "0x1000000000000000000000000000000000000001", "负责数据来源与授权说明"),
            ).lastrowid,
            conn.execute(
                """
                INSERT INTO organizations (name, role, wallet_address, contact)
                VALUES (?, ?, ?, ?)
                """,
                ("机构B 联合实验室", "data_provider", "0x2000000000000000000000000000000000000002", "负责补充训练数据片段"),
            ).lastrowid,
            conn.execute(
                """
                INSERT INTO organizations (name, role, wallet_address, contact)
                VALUES (?, ?, ?, ?)
                """,
                ("联合训练服务方", "trainer", "0x3000000000000000000000000000000000000003", "负责训练任务与模型版本登记"),
            ).lastrowid,
            conn.execute(
                """
                INSERT INTO organizations (name, role, wallet_address, contact)
                VALUES (?, ?, ?, ?)
                """,
                ("第三方审计方", "auditor", "0x4000000000000000000000000000000000000004", "负责哈希复算与证据链复核"),
            ).lastrowid,
        ]

    dataset_a_file = store_example_file(sample / "data" / "iris_org_a.csv", "datasets")
    dataset_b_file = store_example_file(sample / "data" / "iris_org_b.csv", "datasets")
    dataset_a_hash = fetch_one("SELECT sha256 FROM files WHERE id = ?", (dataset_a_file,))["sha256"]
    dataset_b_hash = fetch_one("SELECT sha256 FROM files WHERE id = ?", (dataset_b_file,))["sha256"]

    dataset_payloads = [
        {
            "name": "机构A-Iris训练数据片段",
            "provider": "机构A 数据治理中心",
            "source": "UCI Iris 数据集整理样例，机构A提供 setosa/versicolor 片段",
            "license_type": "research-only",
            "file_id": dataset_a_file,
            "dataset_hash": dataset_a_hash,
        },
        {
            "name": "机构B-Iris补充数据片段",
            "provider": "机构B 联合实验室",
            "source": "UCI Iris 数据集整理样例，机构B提供 virginica/补充片段",
            "license_type": "research-only",
            "file_id": dataset_b_file,
            "dataset_hash": dataset_b_hash,
        },
    ]

    dataset_ids = []
    with connect() as conn:
        for payload in dataset_payloads:
            tx_hash = chain_client.register(
                "DatasetRegistered",
                {
                    "project_id": project_id,
                    "dataset_hash": payload["dataset_hash"],
                    "license_type": payload["license_type"],
                },
            )
            dataset_ids.append(
                conn.execute(
                    """
                    INSERT INTO datasets
                      (project_id, name, provider, source, license_type, file_id, dataset_hash, tx_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        payload["name"],
                        payload["provider"],
                        payload["source"],
                        payload["license_type"],
                        payload["file_id"],
                        payload["dataset_hash"],
                        tx_hash,
                    ),
                ).lastrowid
            )

    code_file = store_example_file(sample / "code" / "train_iris.py", "code")
    config_file = store_example_file(sample / "config" / "iris_config.json", "configs")
    code_hash = fetch_one("SELECT sha256 FROM files WHERE id = ?", (code_file,))["sha256"]
    config_hash = fetch_one("SELECT sha256 FROM files WHERE id = ?", (config_file,))["sha256"]
    task_payload = {
        "project_id": project_id,
        "dataset_ids": dataset_ids,
        "code_hash": code_hash,
        "config_hash": config_hash,
    }
    task_tx = chain_client.register("TrainingTaskRegistered", task_payload)
    with connect() as conn:
        task_id = conn.execute(
            """
            INSERT INTO training_tasks
              (project_id, name, dataset_ids, algorithm, description, code_file_id, config_file_id, code_hash, config_hash, tx_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                "Iris Logistic Regression 联合训练任务",
                json.dumps(dataset_ids),
                "LogisticRegression",
                "使用机构A和机构B登记数据训练轻量分类模型，平台只审计材料哈希与登记关系。",
                code_file,
                config_file,
                code_hash,
                config_hash,
                task_tx,
            ),
        ).lastrowid

    round_payloads = [
        {
            "round_index": 1,
            "organization": "机构A 数据治理中心",
            "local_epochs": 2,
            "sample_count": 75,
            "checkpoint_uri": "ipfs://sample-iris-round-1-org-a",
            "privacy_method": "federated-learning",
        },
        {
            "round_index": 1,
            "organization": "机构B 联合实验室",
            "local_epochs": 2,
            "sample_count": 75,
            "checkpoint_uri": "ipfs://sample-iris-round-1-org-b",
            "privacy_method": "federated-learning",
        },
        {
            "round_index": 2,
            "organization": "联合训练服务方",
            "local_epochs": 1,
            "sample_count": 150,
            "checkpoint_uri": "ipfs://sample-iris-global-checkpoint-v1",
            "privacy_method": "hash-only",
        },
    ]
    with connect() as conn:
        for payload in round_payloads:
            gradient_hash = sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            tx_hash = chain_client.register(
                "TrainingRoundCommitted",
                {
                    "project_id": project_id,
                    "training_task_id": task_id,
                    "round_index": payload["round_index"],
                    "organization": payload["organization"],
                    "gradient_hash": gradient_hash,
                    "checkpoint_uri": payload["checkpoint_uri"],
                    "privacy_method": payload["privacy_method"],
                },
            )
            conn.execute(
                """
                INSERT INTO training_rounds
                  (project_id, training_task_id, round_index, organization, local_epochs, sample_count,
                   gradient_hash, checkpoint_uri, privacy_method, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    task_id,
                    payload["round_index"],
                    payload["organization"],
                    payload["local_epochs"],
                    payload["sample_count"],
                    gradient_hash,
                    payload["checkpoint_uri"],
                    payload["privacy_method"],
                    tx_hash,
                ),
            )

    model_ids = []
    for name, filename, metrics in [
        (
            "Iris 分类模型 v1 - 正常版本",
            "iris_model_v1.pkl",
            '{"accuracy":0.9667,"f1_score":0.9615,"sample_status":"normal"}',
        ),
        (
            "Iris 分类模型 v2 - 篡改检测样例",
            "iris_model_v2.pkl",
            '{"accuracy":0.9733,"f1_score":0.9700,"sample_status":"tampered"}',
        ),
    ]:
        model_file = store_example_file(sample / "models" / filename, "models")
        model_hash = fetch_one("SELECT sha256 FROM files WHERE id = ?", (model_file,))["sha256"]
        model_tx = chain_client.register(
            "ModelVersionRegistered",
            {
                "project_id": project_id,
                "training_task_id": task_id,
                "model_hash": model_hash,
                "metrics": metrics,
            },
        )
        with connect() as conn:
            model_ids.append(
                conn.execute(
                    """
                    INSERT INTO model_versions
                      (project_id, training_task_id, name, model_file_id, metrics, model_hash, tx_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (project_id, task_id, name, model_file, metrics, model_hash, model_tx),
                ).lastrowid
            )

    audit_v1 = create_audit_record(model_ids[0], "样例项目：正常模型版本自动审计")
    tamper_model(model_ids[1])
    audit_v2 = create_audit_record(model_ids[1], "样例项目：模型文件被篡改后的复核审计")

    return {
        "project_id": project_id,
        "organization_ids": organization_ids,
        "dataset_ids": dataset_ids,
        "training_task_id": task_id,
        "normal_model_id": model_ids[0],
        "normal_audit": audit_v1["result"],
        "tampered_model_id": model_ids[1],
        "tampered_audit": audit_v2["result"],
    }


@router.post("/tamper-model")
def tamper_model(model_version_id: int = Form(...)):
    model = fetch_one("SELECT * FROM model_versions WHERE id = ?", (model_version_id,))
    if not model:
        raise HTTPException(status_code=404, detail="未找到模型版本")

    file_row = fetch_one("SELECT * FROM files WHERE id = ?", (model["model_file_id"],))
    if not file_row:
        raise HTTPException(status_code=404, detail="未找到模型文件")

    with open(file_row["stored_path"], "ab") as f:
        f.write(b"\n# tampered-for-integrity-check")

    return {"status": "已篡改", "model_version_id": model_version_id}
