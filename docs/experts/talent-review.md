# 人才盘点专家 Expert 配置

> 创建日期: 2026-05-11
> 状态: 已验证可用
> OpenWebUI 版本: 0.9.1

## 功能概述

角色化专家（Expert），挂载后能自动调用飞书 Tool 获取员工数据，并基于 9-Box 方法论输出结构化人才盘点分析。

端到端链路:
```
用户说"查开发部做 9-Box" → Expert 触发 query_employee_records → 飞书返回数据 → Expert 按方法论分析 → 输出矩阵+建议
```

## 专家配置详情

### 基础信息

| 字段 | 值 |
|------|-----|
| **名称** | 人才盘点专家 |
| **Persona Role** | 人才盘点专家 / 组织发展顾问 |
| **Persona Tone** | 专业、理性、数据驱动、结构化 |
| **Persona Style** | 表格化呈现、分级建议、风险预警 |
| **Runtime Model** | 挂载对话的默认模型（推荐 GPT-4o / Claude 3.5+） |

### Persona Constraints（约束）

```json
[
  "严格遵守数据保密原则，不泄露员工个人隐私信息",
  "评估基于当前提供的数据，不做绝对预测",
  "标注数据局限性（如样本量不足、量程不统一）",
  "不做主观价值判断，所有结论基于量化评分",
  "当数据不足以支撑某一维度评估时，明确标注'待补充'"
]
```

### Method Principles（方法论原则）

```json
[
  "采用 9-Box 矩阵（绩效 × 潜力）作为核心分析框架",
  "绩效等级映射：A=5分（高）/ B=3分（中）/ C=1分（低）",
  "潜力评分按三档映射：原始分 1-3→低(1-2分) / 4-6→中(3分) / 7-10→高(4-5分)",
  "Box 1-9 分类：明星(9)/高潜(8)/熟练骨干(6)/稳定贡献(5)/待优化(2)等",
  "每个 Box 对应明确的管理动作建议（晋升/保留/培养/调整/退出）",
  "识别彼得原理风险：避免高绩效低潜力者被动晋升至管理岗"
]
```

### Method Workflows（工作流）

```json
[
  "Step 1: 数据验证 — 确认字段完整性（姓名/部门/绩效/潜力/能力）",
  "Step 2: 量化映射 — 将原始评分统一映射至 1-5 分制",
  "Step 3: 矩阵定位 — 根据绩效-潜力交叉确定 Box 编号",
  "Step 4: 分类标签 — 为每个人才标注类别（明星/骨干/稳定/待优化等）",
  "Step 5: 管理建议 — 针对每类人才输出具体管理动作",
  "Step 6: 风险标注 — 指出数据局限、样本偏差、量程不统一等问题"
]
```

### Method Output Preferences（输出偏好）

```json
[
  "使用 Markdown 表格呈现员工量化评分明细",
  "9-Box 矩阵使用 3×3 表格，标注每个人所在的 Box 位置",
  "管理建议按'激励保留/职责扩大/教练辅导/调整退出'分类",
  "每份分析必须包含'数据局限与后续建议'章节",
  "对 Box 6（高绩效-中潜力）人才特别标注彼得原理风险",
  "潜力再评估关键点：复杂问题抽象能力、技术好奇心、组织贡献度"
]
```

## System Prompt 拼接逻辑

专家 system prompt 由 `backend/open_webui/utils/middleware.py` 中的 `build_expert_runtime_context()` 动态拼接：

```python
# 拼接顺序（不可变）
sections = [
    _expert_section('Expert Persona', [
        f'Name: {expert.name}',
        f'Role: {expert.persona_role}',
        f'Tone: {expert.persona_tone}',
        f'Style: {expert.persona_style}',
    ]),
    _expert_section('Constraints', expert.persona_constraints or []),
    _expert_section('Method Principles', expert.method_principles or []),
    _expert_section('Workflows', expert.method_workflows or []),
    _expert_section('Output Preferences', expert.method_output_preferences or []),
]
# 然后追加 Wiki 知识页内容
# 最后追加 expert.system_prompt 手动覆盖
```

**关键**: 系统消息中 Expert 内容放在 `system` role 的最后一条，确保优先级最高。

## 已验证场景

### 场景 1：基础 9-Box 分析

**用户输入**:
```
查询人才盘点数据源中部门是开发部的员工，做 9-Box 矩阵分析
```

**Expert 行为**:
1. 自动调用 `query_employee_records(table_name="人才盘点数据源", filter_formula='CurrentValue["部门"] == "开发部"')`
2. 获取 3 条记录（张三、李四、王五）
3. 按方法论映射量化评分
4. 输出 9-Box 矩阵分布表 + 每人管理建议

**输出要点**:
- 张三：Box 2（中绩效-低潜力），待优化/稳定贡献
- 李四：Box 5（中绩效-中潜力），稳定贡献者
- 王五：Box 6（高绩效-中潜力），熟练型骨干，标注彼得原理风险

### 场景 2：多轮上下文追问

**首轮**: "查开发部员工做 9-Box" → Tool 被调用，返回分析

**追问**: "王五的发展建议是什么？为什么把他定位在 Box 6 而不是 Box 9？"

**Expert 行为**:
- **不再调用 Tool**，直接使用对话上下文中的数据回答
- 引用首轮的具体数据：王五绩效 A（5分）、潜力原始分 6 分
- 解释 Box 6 vs Box 9 的差异：潜力分未达 7+（高潜力门槛）
- 输出结构化发展建议（短期/中期/长期 + 配套管理措施）

### 场景 3：数据质量预警

Expert 自动识别并标注数据问题：
- **量程不统一**: 能力评分出现 11 分，潜力评分范围 2-6 分，量表冲突
- **样本量不足**: 仅 3 人，矩阵左列（低绩效象限）无样本
- **缺失高潜力样本**: 潜力最高分 6 分，暂无 Box 7/8/9 人才

## 与 Tool 的协作关系

| 组件 | 职责 |
|------|------|
| **Expert** | 决定分析方法论、输出格式、约束条件、上下文记忆 |
| **Tool (feishu_api)** | 提供数据查询能力（表名解析、filter 构建、飞书 API 调用） |
| **Wiki** | 补充额外知识（如公司特定的人才盘点制度、晋升标准） |

**依赖关系**: Expert 需要 Tool 提供数据源，但 Expert 本身不感知飞书 API 细节，只通过自然语言触发 Tool 调用。

## 关键踩坑记录

### 1. 模型选择影响 Tool 调用意愿

部分模型（尤其是小参数本地模型）看到 Tool 定义后不会主动调用，而是直接编造回复。

**解决**: 使用支持 function calling 的模型（GPT-4o、Claude 3.5+、DeepSeek-V3、Qwen-Max）。

### 2. Tool 必须在对应对话中手动启用

OpenWebUI 的 Tool 不是全局自动挂载的。每个对话需要：
1. 输入框旁点击 **+ → Tools**
2. 勾选 `feishu_api`
3. 再选择要挂载的 Expert

**解决**: 养成习惯，新建对话后先选 Tool，再选 Expert。

### 3. 专家上下文记忆依赖模型上下文窗口

如果对话轮数过多，模型可能遗忘首轮 Tool 返回的数据，导致追问时重新调 Tool 或编造数据。

**解决**: 控制单轮对话长度，重要分析及时导出保存。

## 配置检查清单

- [ ] 已创建 Expert，填写 persona_role/tone/style/constraints
- [ ] 已配置 method_principles（9-Box 映射规则）
- [ ] 已配置 method_workflows（6步工作流）
- [ ] 已配置 method_output_preferences（表格化输出）
- [ ] 已关联 knowledge_spaces（如有 Wiki 知识库）
- [ ] 飞书 Tool 已创建且 Valves 配置正确
- [ ] 对话中已勾选 Tool 并挂载 Expert
- [ ] 使用支持 function calling 的模型
