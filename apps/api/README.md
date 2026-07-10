# API Service

后端服务模块，负责业务 API、文件处理、哈希计算、审计验证和链交互。

## 建议技术栈

- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- web3.py

## 资源模块

- projects
- organizations
- datasets
- training_tasks
- model_versions
- audit_records
- files

## 当前接口

- `GET /api/health`
- `GET/POST /api/projects`
- `GET/POST /api/datasets`
- `GET/POST /api/training-tasks`
- `GET/POST /api/model-versions`
- `GET/POST /api/audits`
- `GET /api/evidence-chain/{model_version_id}`
- `GET /api/chain/status`
- `POST /api/samples/tamper-model`

## 说明

第一版使用 SQLite 和本地文件系统。链上登记通过动态客户端完成：如果检测到 Hardhat 部署文件且 RPC 可连接，则使用 web3.py 调用 `contracts/AuditRegistry.sol`；否则使用 `MockChainClient` 生成模拟交易哈希。
