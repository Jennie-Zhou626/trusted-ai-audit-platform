import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "http://127.0.0.1:8000/api";

type Project = { id: number; name: string; description: string; created_at: string };
type Organization = {
  id: number;
  name: string;
  role: string;
  wallet_address: string;
  contact: string;
  created_at: string;
};
type Dataset = {
  id: number;
  project_id: number;
  name: string;
  provider: string;
  source: string;
  license_type: string;
  dataset_hash: string;
  tx_hash: string;
};
type TrainingTask = {
  id: number;
  project_id: number;
  name: string;
  dataset_ids: string;
  algorithm: string;
  description: string;
  code_hash: string;
  config_hash: string;
  tx_hash: string;
};
type TrainingRound = {
  id: number;
  project_id: number;
  training_task_id: number;
  round_index: number;
  organization: string;
  local_epochs: number;
  sample_count: number;
  gradient_hash: string;
  checkpoint_uri: string;
  privacy_method: string;
  tx_hash: string;
};
type ModelVersion = {
  id: number;
  project_id: number;
  training_task_id: number;
  name: string;
  metrics: string;
  model_hash: string;
  tx_hash: string;
};
type AuditRecord = {
  id: number;
  model_version_id: number;
  result: string;
  reason: string;
  checks: string;
  tx_hash: string;
  created_at: string;
};
type ChainStatus = { client: string; deployment_exists: boolean; mode: string };
type EvidenceChain = {
  datasets: Dataset[];
  training_task: TrainingTask | null;
  training_rounds: TrainingRound[];
  model_version: ModelVersion;
  audits: AuditRecord[];
};
type AuditReport = {
  model_version: ModelVersion;
  training_task: TrainingTask;
  datasets: Dataset[];
  training_rounds: TrainingRound[];
  latest_audit: AuditRecord | null;
  latest_checks: Array<{ item: string; expected: string; actual: string; passed: boolean; message: string }>;
  score: number;
  trust_level: "high" | "medium" | "low";
  strengths: string[];
  warnings: string[];
  recommendations: string[];
};

type DataState = {
  projects: Project[];
  organizations: Organization[];
  datasets: Dataset[];
  tasks: TrainingTask[];
  rounds: TrainingRound[];
  models: ModelVersion[];
  audits: AuditRecord[];
  chain: ChainStatus | null;
};

type RoleKey = "data_provider" | "trainer" | "auditor" | "regulator";
type WriteScope = "base" | "dataset" | "training" | "audit";

const emptyState: DataState = {
  projects: [],
  organizations: [],
  datasets: [],
  tasks: [],
  rounds: [],
  models: [],
  audits: [],
  chain: null,
};

const roleOptions: Array<{ value: RoleKey; label: string; description: string }> = [
  { value: "data_provider", label: "数据提供方", description: "登记机构、项目和数据集" },
  { value: "trainer", label: "训练方", description: "登记训练任务、协同轮次和模型版本" },
  { value: "auditor", label: "审计方", description: "发起审计、复核篡改检测" },
  { value: "regulator", label: "监管方", description: "只读查看证据链和报告" },
];

const writePermissions: Record<RoleKey, WriteScope[]> = {
  data_provider: ["base", "dataset"],
  trainer: ["training"],
  auditor: ["audit"],
  regulator: [],
};

const scopeLabels: Record<WriteScope, string> = {
  base: "基础信息维护",
  dataset: "数据集登记",
  training: "训练过程登记",
  audit: "审计操作",
};

function canWrite(role: RoleKey, scope: WriteScope) {
  return writePermissions[role].includes(scope);
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API}${path}`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function postEmpty<T>(path: string, body: URLSearchParams): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function deleteJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function shortHash(value: string) {
  if (!value) return "-";
  return value.length > 18 ? `${value.slice(0, 10)}...${value.slice(-8)}` : value;
}

function roleLabel(role: string) {
  const labels: Record<string, string> = {
    data_provider: "数据提供方",
    trainer: "训练方",
    auditor: "审计方",
    regulator: "监管/观察方",
  };
  return labels[role] ?? role;
}

function privacyLabel(value: string) {
  const labels: Record<string, string> = {
    "hash-only": "仅哈希存证",
    "federated-learning": "联邦学习摘要",
    "zk-proof-planned": "ZKP 预留",
    "homomorphic-planned": "同态加密预留",
  };
  return labels[value] ?? value;
}

function trustLabel(level: string) {
  if (level === "high") return "高可信";
  if (level === "medium") return "中等可信";
  return "低可信";
}

function auditResultLabel(result?: string) {
  if (result === "passed") return "通过";
  if (result === "failed") return "失败";
  return result || "待审计";
}

function chainModeLabel(mode?: string) {
  if (mode === "web3") return "真实链";
  if (mode === "mock") return "模拟链";
  return "未知";
}

function fieldLabel(field: string) {
  const labels: Record<string, string> = {
    id: "ID",
    name: "名称",
    role: "角色",
    wallet_address: "钱包地址",
    contact: "联系/备注",
    description: "说明",
    created_at: "创建时间",
    provider: "提供机构",
    source: "来源说明",
    license_type: "授权类型",
    dataset_ids: "数据集 ID",
    algorithm: "算法",
    code_hash: "代码哈希",
    config_hash: "配置哈希",
    dataset_hash: "数据哈希",
    model_hash: "模型哈希",
    gradient_hash: "梯度/参数哈希",
    tx_hash: "交易哈希",
    training_task_id: "训练任务 ID",
    round_index: "轮次",
    organization: "参与机构",
    privacy_method: "隐私机制",
    checkpoint_uri: "检查点 URI",
    metrics: "指标",
  };
  return labels[field] ?? field;
}

function displayCell(field: string, value: unknown) {
  const text = String(value ?? "");
  if (field.includes("hash")) return shortHash(text);
  if (field === "privacy_method") return privacyLabel(text);
  if (field === "license_type") {
    const labels: Record<string, string> = {
      "research-only": "科研使用",
      "commercial-allowed": "允许商业使用",
      "no-redistribution": "禁止二次分发",
      "restricted-audit": "仅限审计验证",
    };
    return labels[text] ?? text;
  }
  return text;
}

function downloadText(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildReportMarkdown(report: AuditReport) {
  const checks = report.latest_checks.length
    ? report.latest_checks
        .map((check) => `- ${check.passed ? "通过" : "失败"}：${check.item}（${check.message}）`)
        .join("\n")
    : "- 暂无审计检查项";
  const strengths = report.strengths.map((item) => `- ${item}`).join("\n") || "- 暂无";
  const warnings = report.warnings.map((item) => `- ${item}`).join("\n") || "- 未发现明显风险";
  const recommendations = report.recommendations.map((item) => `- ${item}`).join("\n");

  return `# AI 模型训练过程可信审计报告

## 报告对象

- 模型版本：#${report.model_version.id} ${report.model_version.name}
- 训练任务：#${report.training_task.id} ${report.training_task.name}
- 数据集数量：${report.datasets.length}
- 协同训练轮次：${report.training_rounds.length}
- 可信评分：${report.score} / 100（${trustLabel(report.trust_level)}）

## 审计优势

${strengths}

## 风险提示

${warnings}

## 最新检查项

${checks}

## 改进建议

${recommendations}
`;
}

function App() {
  const [active, setActive] = useState("overview");
  const [currentRole, setCurrentRole] = useState<RoleKey>("data_provider");
  const [data, setData] = useState<DataState>(emptyState);
  const [message, setMessage] = useState("平台已连接，可查看现有记录或继续登记新的审计材料。");
  const [chainModelId, setChainModelId] = useState("");
  const [evidence, setEvidence] = useState<EvidenceChain | null>(null);
  const [auditReport, setAuditReport] = useState<AuditReport | null>(null);

  async function refresh() {
    const [projects, organizations, datasets, tasks, rounds, models, audits, chain] = await Promise.all([
      getJson<Project[]>("/projects"),
      getJson<Organization[]>("/organizations"),
      getJson<Dataset[]>("/datasets"),
      getJson<TrainingTask[]>("/training-tasks"),
      getJson<TrainingRound[]>("/training-rounds"),
      getJson<ModelVersion[]>("/model-versions"),
      getJson<AuditRecord[]>("/audits"),
      getJson<ChainStatus>("/chain/status"),
    ]);
    setData({ projects, organizations, datasets, tasks, rounds, models, audits, chain });
  }

  useEffect(() => {
    refresh().catch((err) => setMessage(`后端连接失败：${err.message}`));
  }, []);

  const selectedProjectId = data.projects[0]?.id ?? 0;
  const latestModelId = chainModelId || String(data.models[0]?.id ?? "");
  const stats = useMemo(
    () => [
      ["项目", data.projects.length],
      ["机构", data.organizations.length],
      ["数据集", data.datasets.length],
      ["训练任务", data.tasks.length],
      ["协同轮次", data.rounds.length],
      ["模型版本", data.models.length],
      ["审计记录", data.audits.length],
    ],
    [data],
  );

  async function handleSubmit(form: HTMLFormElement, path: string, ok: string) {
    const fd = new FormData(form);
    for (const [key, value] of Array.from(fd.entries())) {
      if (typeof value === "string" && value.trim() === "") fd.delete(key);
    }
    try {
      await postForm(path, fd);
      form.reset();
      setMessage(ok);
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleScopedSubmit(form: HTMLFormElement, scope: WriteScope, path: string, ok: string) {
    if (!canWrite(currentRole, scope)) {
      setMessage(`当前角色为${roleLabel(currentRole)}，无权执行${scopeLabels[scope]}。`);
      return;
    }
    await handleSubmit(form, path, ok);
  }

  async function tamperModel(modelVersionId: string) {
    if (!canWrite(currentRole, "audit")) {
      setMessage(`当前角色为${roleLabel(currentRole)}，无权执行审计操作。`);
      return;
    }
    if (!modelVersionId) {
      setMessage("请先输入要篡改的模型版本 ID。");
      return;
    }
    try {
      await postEmpty("/samples/tamper-model", new URLSearchParams({ model_version_id: modelVersionId }));
      setMessage(`模型版本 #${modelVersionId} 的链下文件已被篡改。再次审计应失败。`);
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  async function clearAllData() {
    if (!canWrite(currentRole, "base")) {
      setMessage(`当前角色为${roleLabel(currentRole)}，无权执行基础信息维护。`);
      return;
    }
    if (!window.confirm("确定清空平台中的所有项目、机构、文件索引、训练任务、协同轮次、模型版本和审计记录吗？")) {
      return;
    }
    try {
      await deleteJson("/admin/data");
      setEvidence(null);
      setAuditReport(null);
      setChainModelId("");
      setMessage("平台数据已清空，可以从机构和项目创建开始录入。");
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  async function deleteRecord(path: string, label: string, scope: WriteScope) {
    if (!canWrite(currentRole, scope)) {
      setMessage(`当前角色为${roleLabel(currentRole)}，无权删除${label}记录。`);
      return;
    }
    if (!window.confirm(`确定删除这条${label}记录吗？`)) return;
    try {
      await deleteJson(path);
      setEvidence(null);
      setAuditReport(null);
      setMessage(`${label}记录已删除。`);
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  async function loadEvidence(modelVersionId: string) {
    if (!modelVersionId) {
      setMessage("请输入模型版本 ID。");
      return;
    }
    try {
      const result = await getJson<EvidenceChain>(`/evidence-chain/${modelVersionId}`);
      setEvidence(result);
      setMessage(`已加载模型版本 #${modelVersionId} 的证据链。`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  async function loadAuditReport(modelVersionId: string) {
    if (!modelVersionId) {
      setMessage("请输入模型版本 ID。");
      return;
    }
    try {
      const result = await getJson<AuditReport>(`/audits/report/${modelVersionId}`);
      setAuditReport(result);
      setMessage(`已生成模型版本 #${modelVersionId} 的审计报告。`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  const nav = [
    ["overview", "总览"],
    ["organizations", "机构角色"],
    ["project", "项目"],
    ["dataset", "数据集"],
    ["task", "训练任务"],
    ["rounds", "协同轮次"],
    ["model", "模型版本"],
    ["audit", "审计验证"],
    ["chain", "证据链"],
    ["report", "审计报告"],
  ];

  return (
    <main>
      <aside>
        <div className="brand">
          <span>TA</span>
          <div>
            <strong>可信审计平台</strong>
            <small>可信 AI 审计</small>
          </div>
        </div>
        <nav>
          {nav.map(([id, label]) => (
            <button className={active === id ? "active" : ""} key={id} onClick={() => setActive(id)}>
              {label}
            </button>
          ))}
        </nav>
      </aside>

      <section className="content">
        <header>
          <div>
            <h1>多机构 AI 模型训练过程可信审计平台</h1>
            <p>链下保存材料，链上登记哈希与关键元数据，通过审计复算形成可追溯证据链。</p>
          </div>
          <div className="header-actions">
            <label className="role-switch">
              当前角色
              <select value={currentRole} onChange={(event) => setCurrentRole(event.currentTarget.value as RoleKey)}>
                {roleOptions.map((role) => (
                  <option key={role.value} value={role.value}>
                    {role.label}
                  </option>
                ))}
              </select>
            </label>
            <button className="danger-button" disabled={!canWrite(currentRole, "base")} onClick={() => clearAllData()}>
              清空数据
            </button>
            <button className="ghost" onClick={() => refresh()}>
              刷新
            </button>
          </div>
        </header>

        <div className="chain-status">
          <span>当前角色：{roleLabel(currentRole)}</span>
          <span>{roleOptions.find((role) => role.value === currentRole)?.description}</span>
          <span>链模式：{chainModeLabel(data.chain?.mode)}</span>
          <span>客户端：{data.chain?.client ?? "-"}</span>
          <span>部署文件：{data.chain?.deployment_exists ? "已发现" : "未发现"}</span>
        </div>

        <div className="notice">{message}</div>

        {active === "overview" && (
          <section className="panel">
            <h2>平台总览</h2>
            <div className="stats">
              {stats.map(([label, value]) => (
                <div className="stat" key={label}>
                  <small>{label}</small>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
            <div className="concept-grid">
              <article>
                <small>链下保存</small>
                <strong>数据、代码、配置、模型文件</strong>
                <p>原始材料不直接上链，避免大文件、隐私和成本问题。</p>
              </article>
              <article>
                <small>链上/模拟链登记</small>
                <strong>哈希、时间戳、交易哈希、结论</strong>
                <p>区块链只承担关键节点存证和异步审计职责。</p>
              </article>
              <article>
                <small>协同训练扩展</small>
                <strong>轮次提交、梯度哈希、检查点地址</strong>
                <p>用于模拟联邦学习中的关键轮次记录。</p>
              </article>
              <article>
                <small>审计输出</small>
                <strong>通过 / 失败 + 风险评分</strong>
                <p>通过哈希复算、引用关系和轮次记录生成报告。</p>
              </article>
            </div>
            <EvidencePreview models={data.models} audits={data.audits} rounds={data.rounds} />
          </section>
        )}

        {active === "organizations" && (
          <section className="panel">
            <h2>机构角色管理</h2>
            <PermissionHint allowed={canWrite(currentRole, "base")} scope="base" role={currentRole} />
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleScopedSubmit(e.currentTarget, "base", "/organizations", "机构角色已登记。");
              }}
            >
              <label>
                机构名称
                <input name="name" required placeholder="机构A 数据治理中心" />
              </label>
              <label>
                角色
                <select name="role" required>
                  <option value="data_provider">数据提供方</option>
                  <option value="trainer">训练方</option>
                  <option value="auditor">审计方</option>
                  <option value="regulator">监管/观察方</option>
                </select>
              </label>
              <label>
                钱包地址
                <input name="wallet_address" placeholder="0x..." />
              </label>
              <label>
                联系/备注
                <input name="contact" placeholder="负责人、部门或审计职责" />
              </label>
              <button disabled={!canWrite(currentRole, "base")}>登记机构</button>
            </form>
            <SimpleTable
              rows={data.organizations.map((item) => ({ ...item, role: roleLabel(item.role) }))}
              fields={["id", "name", "role", "wallet_address", "contact", "created_at"]}
              deleteDisabled={!canWrite(currentRole, "base")}
              onDelete={(row) => deleteRecord(`/organizations/${row.id}`, "机构", "base")}
            />
          </section>
        )}

        {active === "project" && (
          <section className="panel">
            <h2>项目管理</h2>
            <PermissionHint allowed={canWrite(currentRole, "base")} scope="base" role={currentRole} />
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleScopedSubmit(e.currentTarget, "base", "/projects", "项目已创建。");
              }}
            >
              <label>
                项目名称
                <input name="name" required placeholder="多机构 AI 模型训练过程可信审计项目" />
              </label>
              <label>
                说明
                <textarea name="description" placeholder="记录项目背景、参与机构和审计范围" />
              </label>
              <button disabled={!canWrite(currentRole, "base")}>创建项目</button>
            </form>
            <SimpleTable
              rows={data.projects}
              fields={["id", "name", "description", "created_at"]}
              deleteDisabled={!canWrite(currentRole, "base")}
              onDelete={(row) => deleteRecord(`/projects/${row.id}`, "项目", "base")}
            />
          </section>
        )}

        {active === "dataset" && (
          <section className="panel">
            <h2>数据集登记</h2>
            <PermissionHint allowed={canWrite(currentRole, "dataset")} scope="dataset" role={currentRole} />
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleScopedSubmit(e.currentTarget, "dataset", "/datasets", "数据集已登记，并生成链上/模拟链交易哈希。");
              }}
            >
              <HiddenProject projectId={selectedProjectId} />
              <label>
                数据集名称
                <input name="name" required placeholder="机构A训练数据片段" />
              </label>
              <label>
                提供机构
                <input name="provider" required placeholder="机构A 数据治理中心" list="organizations-list" />
              </label>
              <label>
                来源说明
                <input name="source" placeholder="机构授权数据 / 公开数据集拆分样例" />
              </label>
              <label>
                授权类型
                <select name="license_type" required>
                  <option value="research-only">科研使用</option>
                  <option value="commercial-allowed">允许商业使用</option>
                  <option value="no-redistribution">禁止二次分发</option>
                  <option value="restricted-audit">仅限审计验证</option>
                </select>
              </label>
              <label>
                数据文件
                <input name="file" type="file" required />
              </label>
              <button disabled={!selectedProjectId || !canWrite(currentRole, "dataset")}>登记数据集</button>
            </form>
            <SimpleTable
              rows={data.datasets}
              fields={["id", "name", "provider", "license_type", "dataset_hash", "tx_hash"]}
              deleteDisabled={!canWrite(currentRole, "dataset")}
              onDelete={(row) => deleteRecord(`/datasets/${row.id}`, "数据集", "dataset")}
            />
          </section>
        )}

        {active === "task" && (
          <section className="panel">
            <h2>训练任务登记</h2>
            <PermissionHint allowed={canWrite(currentRole, "training")} scope="training" role={currentRole} />
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleScopedSubmit(e.currentTarget, "training", "/training-tasks", "训练任务已登记。");
              }}
            >
              <HiddenProject projectId={selectedProjectId} />
              <label>
                任务名称
                <input name="name" required placeholder="联合训练任务 v1" />
              </label>
              <label>
                数据集 ID 列表
                <input name="dataset_ids" required placeholder="[1, 2]" />
              </label>
              <label>
                算法
                <input name="algorithm" required placeholder="LogisticRegression / CNN / FederatedAvg" />
              </label>
              <label>
                任务说明
                <textarea name="description" placeholder="训练目标、输入数据、责任方、审计范围" />
              </label>
              <label>
                训练代码
                <input name="code_file" type="file" required />
              </label>
              <label>
                参数配置
                <input name="config_file" type="file" required />
              </label>
              <button disabled={!selectedProjectId || !canWrite(currentRole, "training")}>登记训练任务</button>
            </form>
            <SimpleTable
              rows={data.tasks}
              fields={["id", "name", "dataset_ids", "algorithm", "code_hash", "config_hash", "tx_hash"]}
              deleteDisabled={!canWrite(currentRole, "training")}
              onDelete={(row) => deleteRecord(`/training-tasks/${row.id}`, "训练任务", "training")}
            />
          </section>
        )}

        {active === "rounds" && (
          <section className="panel">
            <h2>协同训练轮次记录</h2>
            <p className="panel-intro">这里用于模拟联邦学习/多机构协同训练中的关键节点存证：不上传原始数据，只登记轮次、参与机构、梯度摘要和检查点地址。</p>
            <PermissionHint allowed={canWrite(currentRole, "training")} scope="training" role={currentRole} />
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleScopedSubmit(e.currentTarget, "training", "/training-rounds", "协同训练轮次已记录。");
              }}
            >
              <HiddenProject projectId={selectedProjectId} />
              <label>
                训练任务 ID
                <input name="training_task_id" required placeholder={data.tasks[0] ? String(data.tasks[0].id) : "1"} />
              </label>
              <label>
                轮次
                <input name="round_index" type="number" min="1" required defaultValue="1" />
              </label>
              <label>
                参与机构
                <input name="organization" required placeholder="机构A 数据治理中心" list="organizations-list" />
              </label>
              <label>
                本地 Epoch
                <input name="local_epochs" type="number" min="1" defaultValue="1" />
              </label>
              <label>
                样本量
                <input name="sample_count" type="number" min="0" defaultValue="0" />
              </label>
              <label>
                梯度/参数哈希
                <input name="gradient_hash" placeholder="留空则按轮次信息自动生成模拟哈希" />
              </label>
              <label>
                检查点 URI
                <input name="checkpoint_uri" placeholder="ipfs://... 或本地/对象存储地址" />
              </label>
              <label>
                隐私机制
                <select name="privacy_method">
                  <option value="hash-only">仅哈希存证</option>
                  <option value="federated-learning">联邦学习摘要</option>
                  <option value="zk-proof-planned">ZKP 预留</option>
                  <option value="homomorphic-planned">同态加密预留</option>
                </select>
              </label>
              <button disabled={!selectedProjectId || !canWrite(currentRole, "training")}>登记轮次</button>
            </form>
            <SimpleTable
              rows={data.rounds}
              fields={["id", "training_task_id", "round_index", "organization", "privacy_method", "gradient_hash", "checkpoint_uri", "tx_hash"]}
              deleteDisabled={!canWrite(currentRole, "training")}
              onDelete={(row) => deleteRecord(`/training-rounds/${row.id}`, "协同轮次", "training")}
            />
          </section>
        )}

        {active === "model" && (
          <section className="panel">
            <h2>模型版本登记</h2>
            <PermissionHint allowed={canWrite(currentRole, "training")} scope="training" role={currentRole} />
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleScopedSubmit(e.currentTarget, "training", "/model-versions", "模型版本已登记。");
              }}
            >
              <HiddenProject projectId={selectedProjectId} />
              <label>
                模型名称
                <input name="name" required placeholder="分类模型 v1" />
              </label>
              <label>
                训练任务 ID
                <input name="training_task_id" required placeholder={data.tasks[0] ? String(data.tasks[0].id) : "1"} />
              </label>
              <label>
                指标 JSON
                <textarea name="metrics" defaultValue={'{"accuracy":0.9667,"f1_score":0.9615}'} />
              </label>
              <label>
                模型文件
                <input name="model_file" type="file" required />
              </label>
              <button disabled={!selectedProjectId || !canWrite(currentRole, "training")}>登记模型版本</button>
            </form>
            <SimpleTable
              rows={data.models}
              fields={["id", "name", "training_task_id", "metrics", "model_hash", "tx_hash"]}
              deleteDisabled={!canWrite(currentRole, "training")}
              onDelete={(row) => deleteRecord(`/model-versions/${row.id}`, "模型版本", "training")}
            />
          </section>
        )}

        {active === "audit" && (
          <section className="panel">
            <h2>审计验证</h2>
            <PermissionHint allowed={canWrite(currentRole, "audit")} scope="audit" role={currentRole} />
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleScopedSubmit(e.currentTarget, "audit", "/audits", "审计已完成，并登记审计记录。");
              }}
            >
              <label>
                模型版本 ID
                <input name="model_version_id" required placeholder="1" onChange={(e) => setChainModelId(e.currentTarget.value)} />
              </label>
              <label>
                审计说明
                <input name="reason" defaultValue="自动哈希一致性审计" />
              </label>
              <button disabled={!canWrite(currentRole, "audit")}>发起审计</button>
            </form>
            <div className="danger-zone">
              <div>
                <strong>链下材料篡改检测</strong>
                <p>对已登记模型的链下文件追加测试内容，重新审计时会因模型哈希不一致而失败。</p>
              </div>
              <button type="button" disabled={!canWrite(currentRole, "audit")} onClick={() => tamperModel(latestModelId)}>
                篡改当前模型文件
              </button>
            </div>
            <AuditList audits={data.audits} deleteDisabled={!canWrite(currentRole, "audit")} onDelete={(audit) => deleteRecord(`/audits/${audit.id}`, "审计", "audit")} />
          </section>
        )}

        {active === "chain" && (
          <section className="panel">
            <h2>证据链追溯</h2>
            <div className="lookup">
              <label>
                模型版本 ID
                <input value={chainModelId} onChange={(e) => setChainModelId(e.currentTarget.value)} placeholder={data.models[0] ? String(data.models[0].id) : "1"} />
              </label>
              <button onClick={() => loadEvidence(latestModelId)}>查询证据链</button>
            </div>
            {evidence ? <EvidenceDetails evidence={evidence} /> : <EvidencePreview models={data.models} audits={data.audits} rounds={data.rounds} detailed />}
          </section>
        )}

        {active === "report" && (
          <section className="panel">
            <h2>审计报告与可信评分</h2>
            <div className="lookup">
              <label>
                模型版本 ID
                <input value={chainModelId} onChange={(e) => setChainModelId(e.currentTarget.value)} placeholder={data.models[0] ? String(data.models[0].id) : "1"} />
              </label>
              <button onClick={() => loadAuditReport(latestModelId)}>生成报告</button>
            </div>
            {auditReport ? <AuditReportView report={auditReport} /> : <p className="empty">生成报告后，这里会列出可信评分、优势、风险和改进建议。</p>}
          </section>
        )}

        <datalist id="organizations-list">
          {data.organizations.map((org) => (
            <option key={org.id} value={org.name} />
          ))}
        </datalist>
      </section>
    </main>
  );
}

function HiddenProject({ projectId }: { projectId: number }) {
  return <input type="hidden" name="project_id" value={projectId || ""} />;
}

function PermissionHint({ allowed, scope, role }: { allowed: boolean; scope: WriteScope; role: RoleKey }) {
  if (allowed) return null;
  return (
    <p className="permission-hint">
      当前角色为{roleLabel(role)}，无权执行{scopeLabels[scope]}。
    </p>
  );
}

function SimpleTable({
  rows,
  fields,
  onDelete,
  deleteDisabled = false,
}: {
  rows: Record<string, unknown>[];
  fields: string[];
  onDelete?: (row: Record<string, unknown>) => void;
  deleteDisabled?: boolean;
}) {
  if (!rows.length) return <p className="empty">暂无记录</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {fields.map((field) => (
              <th key={field}>{fieldLabel(field)}</th>
            ))}
            {onDelete ? <th>操作</th> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {fields.map((field) => (
                <td key={field}>{displayCell(field, row[field])}</td>
              ))}
              {onDelete ? (
                <td>
                  <button className="table-action danger-button" type="button" disabled={deleteDisabled} onClick={() => onDelete(row)}>
                    删除
                  </button>
                </td>
              ) : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditList({ audits, onDelete, deleteDisabled = false }: { audits: AuditRecord[]; onDelete: (audit: AuditRecord) => void; deleteDisabled?: boolean }) {
  if (!audits.length) return <p className="empty">暂无审计记录</p>;
  return (
    <div className="audit-list">
      {audits.map((audit) => {
        const checks = JSON.parse(audit.checks || "[]") as Array<{ item: string; passed: boolean; message: string }>;
        return (
          <article className="audit-card" key={audit.id}>
            <div>
              <strong>模型 #{audit.model_version_id}</strong>
              <span className={audit.result === "passed" ? "ok" : "bad"}>{auditResultLabel(audit.result)}</span>
            </div>
            <div className="audit-meta">
              <small>{shortHash(audit.tx_hash)}</small>
              <button className="table-action danger-button" type="button" disabled={deleteDisabled} onClick={() => onDelete(audit)}>
                删除
              </button>
            </div>
            <ul>
              {checks.map((check) => (
                <li key={check.item}>
                  <span>{check.item}</span>
                  <b className={check.passed ? "ok" : "bad"}>{check.passed ? "通过" : check.message}</b>
                </li>
              ))}
            </ul>
          </article>
        );
      })}
    </div>
  );
}

function EvidenceDetails({ evidence }: { evidence: EvidenceChain }) {
  const latestAudit = evidence.audits[0];
  const nodes = [
    ...evidence.datasets.map((dataset) => ({
      title: `数据集 #${dataset.id}`,
      desc: `${dataset.name} / ${dataset.provider}`,
      hash: dataset.dataset_hash,
      tx: dataset.tx_hash,
    })),
    evidence.training_task
      ? {
          title: `训练任务 #${evidence.training_task.id}`,
          desc: evidence.training_task.algorithm,
          hash: evidence.training_task.code_hash,
          tx: evidence.training_task.tx_hash,
        }
      : null,
    ...evidence.training_rounds.map((round) => ({
      title: `协同轮次 #${round.round_index}`,
      desc: `${round.organization} / ${round.privacy_method}`,
      hash: round.gradient_hash,
      tx: round.tx_hash,
    })),
    {
      title: `模型版本 #${evidence.model_version.id}`,
      desc: evidence.model_version.name,
      hash: evidence.model_version.model_hash,
      tx: evidence.model_version.tx_hash,
    },
    ...evidence.audits.map((audit) => ({
      title: `审计记录 #${audit.id}`,
      desc: auditResultLabel(audit.result),
      hash: auditResultLabel(audit.result),
      tx: audit.tx_hash,
    })),
  ].filter(Boolean) as Array<{ title: string; desc: string; hash: string; tx: string }>;

  return (
    <>
      <section className="evidence-flow">
        <div className="flow-stage source">
          <span>1</span>
          <small>数据来源</small>
          <strong>{evidence.datasets.length} 个数据集</strong>
          <p>{evidence.datasets.map((dataset) => dataset.provider).join(" / ") || "暂无数据集"}</p>
        </div>
        <div className="flow-connector" />
        <div className="flow-stage task">
          <span>2</span>
          <small>训练任务</small>
          <strong>{evidence.training_task ? `#${evidence.training_task.id}` : "缺失"}</strong>
          <p>{evidence.training_task?.algorithm ?? "未找到训练任务"}</p>
        </div>
        <div className="flow-connector" />
        <div className="flow-stage rounds">
          <span>3</span>
          <small>协同轮次</small>
          <strong>{evidence.training_rounds.length} 条记录</strong>
          <p>{evidence.training_rounds.map((round) => `${round.round_index}:${privacyLabel(round.privacy_method)}`).join(" / ") || "暂无轮次"}</p>
        </div>
        <div className="flow-connector" />
        <div className="flow-stage model">
          <span>4</span>
          <small>模型版本</small>
          <strong>#{evidence.model_version.id}</strong>
          <p>{shortHash(evidence.model_version.model_hash)}</p>
        </div>
        <div className="flow-connector" />
        <div className={`flow-stage audit ${latestAudit?.result === "failed" ? "failed" : "passed"}`}>
          <span>5</span>
          <small>审计结论</small>
          <strong>{auditResultLabel(latestAudit?.result)}</strong>
          <p>{latestAudit ? shortHash(latestAudit.tx_hash) : "暂无审计记录"}</p>
        </div>
      </section>
      <h3 className="section-title">证据链明细</h3>
      <div className="evidence-details">
        {nodes.map((node, index) => (
          <article className="evidence-node" key={`${node.title}-${index}`}>
            <span>{index + 1}</span>
            <div>
              <strong>{node.title}</strong>
              <small>{node.desc}</small>
            </div>
            <dl>
              <dt>对象哈希/状态</dt>
              <dd>{shortHash(node.hash)}</dd>
              <dt>交易哈希</dt>
              <dd>{shortHash(node.tx)}</dd>
            </dl>
          </article>
        ))}
      </div>
    </>
  );
}

function EvidencePreview({
  models,
  audits,
  rounds,
  detailed = false,
}: {
  models: ModelVersion[];
  audits: AuditRecord[];
  rounds: TrainingRound[];
  detailed?: boolean;
}) {
  const model = models[0];
  const audit = model ? audits.find((item) => item.model_version_id === model.id) : undefined;
  if (!model) return <p className="empty">登记模型版本后，这里可查看证据链。</p>;
  const nodes = [
    ["数据集版本", "由训练任务引用"],
    ["训练任务", `task #${model.training_task_id}`],
    ["协同轮次", `${rounds.filter((round) => round.training_task_id === model.training_task_id).length} 条记录`],
    ["模型版本", shortHash(model.model_hash)],
    ["审计结果", audit ? auditResultLabel(audit.result) : "待审计"],
  ];
  return (
    <div className={detailed ? "timeline detailed" : "timeline"}>
      {nodes.map(([title, desc], index) => (
        <div className="node" key={title}>
          <span>{index + 1}</span>
          <strong>{title}</strong>
          <small>{desc}</small>
        </div>
      ))}
    </div>
  );
}

function AuditReportView({ report }: { report: AuditReport }) {
  const exportBaseName = `audit-report-model-${report.model_version.id}`;
  return (
    <div className="report-layout">
      <article className={`score-card ${report.trust_level}`}>
        <small>可信评分</small>
        <strong>{report.score}</strong>
        <span>{trustLabel(report.trust_level)}</span>
      </article>
      <article className="report-card export-card">
        <h3>报告导出</h3>
        <p>导出内容包含模型对象、证据链摘要、可信评分、风险提示、检查项和改进建议。</p>
        <div className="export-actions">
          <button
            type="button"
            onClick={() => downloadText(`${exportBaseName}.md`, buildReportMarkdown(report), "text/markdown;charset=utf-8")}
          >
            导出 Markdown
          </button>
          <button
            className="ghost"
            type="button"
            onClick={() => downloadText(`${exportBaseName}.json`, JSON.stringify(report, null, 2), "application/json;charset=utf-8")}
          >
            导出 JSON
          </button>
        </div>
      </article>
      <article className="report-card">
        <h3>报告对象</h3>
        <p>模型版本：#{report.model_version.id} {report.model_version.name}</p>
        <p>训练任务：#{report.training_task.id} {report.training_task.name}</p>
        <p>数据集数量：{report.datasets.length}，协同轮次：{report.training_rounds.length}</p>
      </article>
      <article className="report-card">
        <h3>优势</h3>
        <ul>
          {report.strengths.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </article>
      <article className="report-card warning">
        <h3>风险</h3>
        <ul>
          {report.warnings.length ? report.warnings.map((item) => <li key={item}>{item}</li>) : <li>未发现明显风险。</li>}
        </ul>
      </article>
      <article className="report-card wide">
        <h3>改进建议</h3>
        <ul>
          {report.recommendations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </article>
      <article className="report-card wide">
        <h3>最新审计检查项</h3>
        {report.latest_checks.length ? (
          <ul className="check-list">
            {report.latest_checks.map((check) => (
              <li key={check.item}>
                <span>{check.item}</span>
                <b className={check.passed ? "ok" : "bad"}>{check.passed ? "通过" : check.message}</b>
              </li>
            ))}
          </ul>
        ) : (
          <p>还没有审计记录。</p>
        )}
      </article>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
