import shutil
from pathlib import Path
from typing import Iterable

from ..config import UPLOAD_DIR
from ..db import connect, fetch_all


def delete_file_paths(paths: Iterable[str]) -> None:
    for path in paths:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass


def delete_files_by_ids(file_ids: Iterable[int]) -> None:
    ids = [int(file_id) for file_id in file_ids if file_id]
    if not ids:
        return

    placeholders = ",".join("?" for _ in ids)
    rows = fetch_all(f"SELECT stored_path FROM files WHERE id IN ({placeholders})", ids)
    delete_file_paths(row["stored_path"] for row in rows)

    with connect() as conn:
        conn.execute(f"DELETE FROM files WHERE id IN ({placeholders})", ids)


def reset_all_runtime_data() -> None:
    with connect() as conn:
        conn.executescript(
            """
            DELETE FROM audit_records;
            DELETE FROM model_versions;
            DELETE FROM training_rounds;
            DELETE FROM training_tasks;
            DELETE FROM datasets;
            DELETE FROM files;
            DELETE FROM organizations;
            DELETE FROM projects;
            DELETE FROM sqlite_sequence
              WHERE name IN ('audit_records', 'model_versions', 'training_rounds', 'datasets', 'files', 'organizations', 'projects');
            """
        )

    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
