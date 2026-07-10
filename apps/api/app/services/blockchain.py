import json
import os
import time
from pathlib import Path
from typing import Any

from ..config import DEPLOYMENT_PATH
from ..utils.hashing import sha256_text


class MockChainClient:
    """Replace this with web3.py without changing router code."""

    def register(self, event_type: str, payload: dict[str, Any]) -> str:
        body = json.dumps(
            {"event_type": event_type, "payload": payload, "time": time.time()},
            ensure_ascii=False,
            sort_keys=True,
        )
        return "0x" + sha256_text(body)


class Web3ChainClient:
    def __init__(self, deployment_path: Path = DEPLOYMENT_PATH) -> None:
        from web3 import Web3

        deployment = json.loads(deployment_path.read_text(encoding="utf-8-sig"))
        self.w3 = Web3(
            Web3.HTTPProvider(
                deployment.get("rpc_url", "http://127.0.0.1:8545"),
                request_kwargs={"timeout": 0.4},
            )
        )
        if not self.w3.is_connected():
            raise RuntimeError("Hardhat RPC is not connected")

        private_key = os.getenv(
            "AUDIT_CHAIN_PRIVATE_KEY",
            deployment.get("private_key", ""),
        )
        if not private_key:
            raise RuntimeError("Missing blockchain private key")

        self.account = self.w3.eth.account.from_key(private_key)
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(deployment["address"]),
            abi=deployment["abi"],
        )

    def register(self, event_type: str, payload: dict[str, Any]) -> str:
        method_name, args = self._map_call(event_type, payload)
        method = getattr(self.contract.functions, method_name)(*args)
        tx = method.build_transaction(
            {
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": 1_000_000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        if receipt.status != 1:
            raise RuntimeError(f"Blockchain transaction failed: {tx_hash.hex()}")
        return tx_hash.hex()

    def _map_call(self, event_type: str, payload: dict[str, Any]) -> tuple[str, list[Any]]:
        if event_type == "DatasetRegistered":
            return "registerDataset", [
                int(payload["project_id"]),
                payload["dataset_hash"],
                payload["license_type"],
            ]
        if event_type == "TrainingTaskRegistered":
            return "registerTrainingTask", [
                int(payload["project_id"]),
                json.dumps(payload["dataset_ids"], ensure_ascii=False),
                payload["code_hash"],
                payload["config_hash"],
            ]
        if event_type == "TrainingRoundCommitted":
            return "commitTrainingRound", [
                int(payload["project_id"]),
                int(payload["training_task_id"]),
                int(payload["round_index"]),
                payload["organization"],
                payload["gradient_hash"],
                payload.get("checkpoint_uri", ""),
                payload.get("privacy_method", "hash-only"),
            ]
        if event_type == "ModelVersionRegistered":
            return "registerModelVersion", [
                int(payload["project_id"]),
                int(payload["training_task_id"]),
                payload["model_hash"],
                payload.get("metrics", "{}"),
            ]
        if event_type == "AuditRecordRegistered":
            return "registerAuditRecord", [
                int(payload.get("project_id", 0)),
                int(payload["model_version_id"]),
                payload["result"],
                payload.get("reason", ""),
            ]
        raise ValueError(f"Unsupported blockchain event: {event_type}")


def create_chain_client():
    if DEPLOYMENT_PATH.exists():
        try:
            return Web3ChainClient()
        except Exception:
            return MockChainClient()
    return MockChainClient()


class DynamicChainClient:
    def register(self, event_type: str, payload: dict[str, Any]) -> str:
        try:
            return create_chain_client().register(event_type, payload)
        except ValueError:
            return MockChainClient().register(event_type, payload)

    def active_client_name(self) -> str:
        return create_chain_client().__class__.__name__


chain_client = DynamicChainClient()
