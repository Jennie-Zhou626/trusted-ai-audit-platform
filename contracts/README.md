# Contracts

智能合约模块，负责链上证据登记。

## 第一阶段合约接口

- `registerDataset`
- `registerTrainingTask`
- `registerModelVersion`
- `registerAuditRecord`
- `getDataset`
- `getTrainingTask`
- `getModelVersion`
- `getAuditRecord`

## 设计原则

链上只保存哈希、编号、时间戳、操作者地址和必要元数据，不保存原始数据、模型文件或完整日志。

## 当前文件

- `contracts/AuditRegistry.sol`：第一版登记合约草案。

后端已支持通过 web3.py 调用真实合约；当 Hardhat RPC 或部署文件不可用时，会自动回退到 `MockChainClient` 生成模拟交易哈希。

## 本地链使用

启动 Hardhat 节点：

```powershell
..\scripts\start-chain.ps1
```

部署合约：

```powershell
..\scripts\deploy-contract.ps1
```

部署脚本会生成 `deployment.json`，后端会自动读取该文件并优先使用 web3.py 进行链上登记。
