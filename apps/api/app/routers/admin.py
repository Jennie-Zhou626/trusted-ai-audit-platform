from fastapi import APIRouter

from ..services.cleanup import reset_all_runtime_data

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.delete("/data")
def clear_all_data():
    reset_all_runtime_data()
    return {"status": "已清空"}
