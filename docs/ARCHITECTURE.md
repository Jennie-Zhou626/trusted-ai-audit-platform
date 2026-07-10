# Architecture

## 分层

```text
网页交互层
  -> 后端服务层
  -> 训练适配层
  -> 区块链合约层
  -> 链下文件与元数据层
```

## 核心链路

```text
数据集登记
  -> 训练任务登记
  -> 模型版本登记
  -> 审计验证
  -> 证据链追溯
```

## 技术栈

- Frontend: React + Vite + TypeScript
- Backend: FastAPI + Pydantic + SQLAlchemy
- Database: SQLite first, PostgreSQL later if needed
- Blockchain: Solidity + Hardhat local chain
- Chain Interaction: web3.py
- Training Adapter: Python
- Storage: Local filesystem first
