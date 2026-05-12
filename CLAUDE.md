# Expert Platform OS — 项目级 AI Coding 规范

> 本项目的 AI Coding 工作流遵循 RED Protocol（Research → Execute → Defend）。
> 用户级全局配置见 `~/.claude/CLAUDE.md`（含 RTK、Karpathy Guidelines 等）。

---

## 项目概况

| 项 | 值 |
|---|-----|
| **名称** | expert-platform-os |
| **定位** | OpenWebUI Fork + Expert（专家）+ Wiki（知识库编译）+ Skills（工具） |
| **前端** | SvelteKit |
| **后端** | FastAPI（Python） |
| **数据库** | SQLite（默认） |
| **部署** | Docker |
| **自定义模块** | Expert 系统、Wiki 编译、飞书 Tool |

---

## RED Protocol（强制三阶段）

写代码前必须完成 Research，交付时必须分层，提交前必须过检查清单。

### Phase 1: RESEARCH（研究）— 未完成禁止输出代码

当用户要求编写/修改/调试代码时，先完成扫描：

**A. 环境扫描（必须问或确认）**
- [ ] OpenWebUI 版本（当前 0.9.1）
- [ ] 操作系统 & Shell 类型（PowerShell / Bash / Zsh / cmd）
- [ ] 容器化？Docker / K8s / 本地运行？
- [ ] 日志怎么看？`docker logs` / 文件路径 / 前端看板？
- [ ] 调试手段：断点 / print / 远程 debug？

**B. 需求拆解（必须用用户原话复述）**
- [ ] 用户的真实目标是什么？（不是"写个Tool"，而是"能查飞书表格数据"）
- [ ] 输入是什么？输出是什么？
- [ ] 有哪些已知的外部依赖？（飞书 API、LLM 模型、数据库）
- [ ] 有哪些已知的限制？（权限、网络、编码、Docker 无网络）

**C. 假设声明（必须明确说出我的假设）**
- [ ] 我假设...（例如：我假设飞书表格字段是英文）
- [ ] 如果假设错误，影响范围是...

**完成以上前，只能输出问题和确认项，禁止输出任何代码、命令或配置。**

### Phase 2: EXECUTE（执行）— 分层交付，每层必须验证

**Layer 1：骨架（Skeleton）**
- 只写接口定义、函数签名、数据结构
- 不实现任何逻辑
- 用户确认：接口设计是否符合预期？

**Layer 2：核心路径（Happy Path）**
- 只实现主流程，不处理错误、不处理边界
- 用户确认：主流程是否能跑通？

**Layer 3：边界与防御（Edge Cases & Defense）**
- 错误处理、权限校验、超时重试、日志打印
- 用户确认：异常场景是否覆盖？

**禁止跳层。Layer 1 未确认，不能输出 Layer 2。**

### Phase 3: DEFEND（防御）— 提交前必须过检查清单

**A. 环境兼容性**
- [ ] 路径分隔符：Windows `\` vs Unix `/`
- [ ] 编码：UTF-8 / GBK，是否涉及中文？
- [ ] 权限：是否需要 sudo / admin？
- [ ] 依赖：是否需要 pip install / npm install？（Docker 无网络时注意离线安装）

**B. 可观测性**
- [ ] 关键步骤是否有日志输出？
- [ ] 错误是否有明确提示，而不是抛异常？
- [ ] 用户如何验证结果？（curl？浏览器？日志？）

**C. 回滚安全**
- [ ] 修改是否可逆？如果错了怎么恢复？
- [ ] 是否影响现有功能？（touch 了哪些文件？）

**未完成检查清单，禁止提交。**

---

## Skill 自动加载规则

检测到以下场景时，必须主动加载对应 skill：

| 场景关键词 | 必须加载的 Skill | 用途 |
|-----------|-----------------|------|
| "报错"/"error"/"失败了" | diagnose | 系统性排查 bug |
| "帮我写"/"帮我开发"/"帮我做一个" | prototype + grill-me | 先做原型设计，再质疑需求 |
| "重构"/"优化"/"改得更好" | simplify | 先 review 再动手 |
| "测试"/"test"/"验证" | tdd | 先写测试再写实现 |
| "拆任务"/"todo"/"计划" | to-issues | 把需求拆成可执行 issue |

**不能等用户喊关键词。检测到场景必须主动加载。**

---

## 用户提示词指导（契约式交付）

当用户给出模糊指令时（如"帮我写个 Tool"），我必须：
1. 不直接写代码
2. 输出一份**"上下文包裹器模板"**，让用户填空
3. 等用户填完再进入 RED 协议的 Phase 1

**上下文包裹器模板**：
```
我需要做 [目标]，上下文如下：

【环境】
- OpenWebUI 版本：___
- 操作系统：___
- 部署方式：___

【目标】
- 输入：___
- 输出：___
- 核心流程：___

【已知信息】
- API 文档地址：___
- 已有凭证/权限：___
- 已有代码/配置：___

【约束】
- 不能修改的文件：___（如 middleware.py、experts.py）
- 必须遵守的规范：___
- 性能/安全要求：___

【验收标准】
- [ ] 验收项 1
- [ ] 验收项 2

请按 RED 协议：先确认需求，再分层交付。
```

---

## 项目特定的踩坑记录

### 1. OpenWebUI Tool 机制
- Tool 类中所有 `async def` 方法都会暴露给 LLM
- **不要暴露辅助方法**（如 `list_tables`），否则 LLM 会偷懒只调辅助方法
- Valves 配置和代码保存是**两个独立操作**，保存代码后必须单独保存 Valves
- Tool 代码通过 `exec()` 动态执行，**必须**用 Pydantic `BaseModel` + `Field()` 定义 Valves

### 2. Docker 环境限制
- Docker build 时无网络，不能用 `npm ci` 或 `pip install`
- `pyodide:fetch` 在容器内会超时，build 脚本中要去掉
- Docker logs 输出是 UTF-8，PowerShell 默认 GBK，需要 `docker logs | Select-String` 过滤

### 3. Expert 系统依赖
- `backend/open_webui/utils/middleware.py` 包含 `build_expert_runtime_context()`，是 Expert 核心
- **绝对不能碰这个文件**的上游更新（上游 dev 分支会删掉 Expert 逻辑）
- Expert 的 system prompt 拼接顺序：Persona → Constraints → Method → Wiki → Override

### 4. 飞书 API 已知问题
- GET `/records?filter=...` 容易因 URL 编码出错，**统一用 POST `/records/search`**
- filter 参数需要是 JSON 字符串，不是 `CurrentValue[