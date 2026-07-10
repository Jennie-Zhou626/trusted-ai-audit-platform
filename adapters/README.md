# Training Adapters

训练适配器模块，负责接入平台内置轻量训练或外部训练结果。

## 职责

- 读取 `manifest.json`。
- 执行轻量训练或导入外部结果。
- 输出统一审计材料。
- 生成数据、代码、配置和模型哈希。

## 统一输出

- `dataset_hash`
- `code_hash`
- `config_hash`
- `model_hash`
- `metrics`
- `logs`
