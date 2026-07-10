# Scripts

脚本目录，用于放置初始化、部署、自测和样例数据准备脚本。

## 计划脚本

- 初始化数据库
- 启动本地链
- 部署合约
- 准备示例数据
- 执行端到端自测

## 当前脚本

- `start-api.ps1`：启动 FastAPI 后端。
- `start-web.ps1`：启动 Vite 前端。
- `start-chain.ps1`：启动 Hardhat 本地链。
- `deploy-contract.ps1`：编译并部署 `AuditRegistry` 合约。
- `smoke-test-api.ps1`：运行后端闭环自测。
- `seed-showcase-project.ps1`：生成一组本地样例数据，便于开发调试。

Windows 如果禁止执行 PowerShell 脚本，可以直接使用同名 `.cmd` 脚本：

- `start-api.cmd`
- `start-web.cmd`
- `start-chain.cmd`
- `deploy-contract.cmd`
- `smoke-test-api.cmd`
- `seed-showcase-project.cmd`
