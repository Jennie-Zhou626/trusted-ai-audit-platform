from fastapi import APIRouter, Form, HTTPException

from ..db import connect, fetch_all, fetch_one

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("")
def list_organizations(role: str | None = None):
    if role:
        return fetch_all("SELECT * FROM organizations WHERE role = ? ORDER BY id DESC", (role,))
    return fetch_all("SELECT * FROM organizations ORDER BY id DESC")


@router.post("")
def create_organization(
    name: str = Form(...),
    role: str = Form(...),
    wallet_address: str = Form(""),
    contact: str = Form(""),
):
    if role not in {"data_provider", "trainer", "auditor", "regulator"}:
        raise HTTPException(status_code=400, detail="不支持的机构角色")

    with connect() as conn:
        org_id = conn.execute(
            """
            INSERT INTO organizations (name, role, wallet_address, contact)
            VALUES (?, ?, ?, ?)
            """,
            (name, role, wallet_address, contact),
        ).lastrowid

    return fetch_one("SELECT * FROM organizations WHERE id = ?", (org_id,))


@router.delete("/{organization_id}")
def delete_organization(organization_id: int):
    if not fetch_one("SELECT id FROM organizations WHERE id = ?", (organization_id,)):
        raise HTTPException(status_code=404, detail="未找到机构")

    with connect() as conn:
        conn.execute("DELETE FROM organizations WHERE id = ?", (organization_id,))
    return {"status": "已删除", "organization_id": organization_id}
