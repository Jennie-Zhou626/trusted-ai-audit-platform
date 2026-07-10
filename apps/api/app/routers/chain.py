from fastapi import APIRouter

from ..config import DEPLOYMENT_PATH
from ..services.blockchain import chain_client

router = APIRouter(prefix="/api/chain", tags=["chain"])


@router.get("/status")
def chain_status():
    client_name = chain_client.active_client_name()
    return {
        "client": client_name,
        "deployment_exists": DEPLOYMENT_PATH.exists(),
        "mode": "web3" if client_name == "Web3ChainClient" else "mock",
    }
