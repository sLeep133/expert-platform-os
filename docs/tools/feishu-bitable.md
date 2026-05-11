# 飞书多维表格数据查询 Tool (feishu_api)

> 创建日期: 2026-05-11
> 状态: 已验证可用
> OpenWebUI 版本: 0.9.1

## 功能概述

Native Tool，支持通过自然语言查询飞书多维表格（Bitable）中的员工记录。

端到端链路:
```
用户说"查开发部员工" → LLM 生成 filter → Tool 解析并调用飞书 API → 返回结构化 JSON
```

## 核心代码

```python
import requests
import json
import re
from pydantic import BaseModel, Field


def _parse_filter(filter_formula, field_map):
    if not filter_formula:
        return None, None
    try:
        json.loads(filter_formula)
        return filter_formula, None
    except json.JSONDecodeError:
        pass

    m = re.search(r'CurrentValue\[("\')([^"\']+)\1\]\s*==\s*(["\'])([^"\']+)\3', filter_formula)
    if not m:
        m = re.search(r'([\w\u4e00-\u9fff]+)\s*==\s*(["\']?)([^"\',\s]+)\2', filter_formula)

    if not m:
        return None, f"Cannot parse filter: {filter_formula}"

    field_key = m.group(2) if 'CurrentValue' in filter_formula[:20] else m.group(1)
    value = m.group(4) if 'CurrentValue' in filter_formula[:20] else m.group(3)

    matched_field = None
    lower_key = field_key.lower()

    if lower_key in field_map:
        matched_field = field_map[lower_key][0]
    else:
        for k, (name, _) in field_map.items():
            if lower_key in k or k in lower_key:
                matched_field = name
                break

    if not matched_field:
        available = sorted(list(set(name for name, _ in field_map.values())))
        return None, f"Field '{field_key}' not found. Available fields: {available}"

    return json.dumps({
        "conjunction": "and",
        "conditions": [{"field_name": matched_field, "operator": "is", "value": [value]}]
    }, ensure_ascii=False), None


class Tools:
    def __init__(self):
        self.valves = self.Valves()

    class Valves(BaseModel):
        app_id: str = Field(default="", description="Feishu App ID")
        app_secret: str = Field(default="", description="Feishu App Secret")
        base_url: str = Field(default="https://open.feishu.cn", description="Feishu Open API Base URL")
        default_app_token: str = Field(default="", description="Default Bitable app_token")
        default_table_name: str = Field(default="", description="Default table display name")

    def _get_token(self):
        url = f"{self.valves.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, headers={"Content-Type": "application/json"},
                           json={"app_id": self.valves.app_id, "app_secret": self.valves.app_secret}, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"Get token failed: {data}")
        return data["tenant_access_token"]

    def _list_tables(self, token, app_token):
        url = f"{self.valves.base_url}/open-apis/bitable/v1/apps/{app_token}/tables"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            return []
        return [(t.get("name", ""), t.get("table_id", "")) for t in data.get("data", {}).get("items", [])]

    def _get_fields(self, token, app_token, table_id):
        url = f"{self.valves.base_url}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            return {}
        field_map = {}
        for f in data.get("data", {}).get("items", []):
            name = f.get("field_name", "")
            if name:
                field_map[name.lower()] = (name, f.get("field_id", ""))
        return field_map

    def _resolve_table_id(self, tables, table_name):
        for name, tid in tables:
            if name == table_name:
                return tid
        for name, tid in tables:
            if table_name in name or name in table_name:
                return tid
        return tables[0][1] if tables else ""

    async def query_employee_records(self, table_name="", filter_formula="", user_id="") -> str:
        """
        查询飞书多维表格中的员工记录。这是唯一可用的数据查询工具。
        传入 table_name 和 filter_formula 即可直接查询，无需先获取表列表。
        :param table_name: 表显示名称，如"人才盘点数据源"。不传则使用 Valves 中的 default_table_name。
        :param filter_formula: 过滤条件，如 CurrentValue["部门"] == "开发部"
        :param user_id: 精确匹配员工ID
        """
        if not self.valves.app_id or not self.valves.app_secret:
            return json.dumps({"error": "Please configure app_id and app_secret in Valves"}, ensure_ascii=False)

        token = self._get_token()
        app_token = self.valves.default_app_token
        if not app_token:
            return json.dumps({"error": "Please configure default_app_token in Valves"}, ensure_ascii=False)

        _table_name = table_name.strip() or self.valves.default_table_name
        if not _table_name:
            return json.dumps({"error": "Please provide table_name"}, ensure_ascii=False)

        tables = self._list_tables(token, app_token)
        table_id = self._resolve_table_id(tables, _table_name)
        if not table_id:
            return json.dumps({"error": "Table not found", "available_tables": [n for n, _ in tables]}, ensure_ascii=False)

        field_map = self._get_fields(token, app_token, table_id)

        body = {}
        if user_id:
            body["filter"] = {"conjunction": "and", "conditions": [{"field_name": "员工ID", "operator": "is", "value": [user_id]}]}
        elif filter_formula:
            parsed, error = _parse_filter(filter_formula, field_map)
            if error:
                return json.dumps({"error": error, "available_fields": sorted(list(set(name for name, _ in field_map.values())))}, ensure_ascii=False)
            body["filter"] = json.loads(parsed)

        print(f"[TOOL DEBUG] table='{_table_name}' id='{table_id}'", flush=True)
        print(f"[TOOL DEBUG] body={body}", flush=True)

        url = f"{self.valves.base_url}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
        resp = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body if body else {}, timeout=30)

        print(f"[TOOL DEBUG] status={resp.status_code} body={resp.text[:500]}", flush=True)

        if resp.status_code != 200:
            return json.dumps({"error": f"API error {resp.status_code}", "detail": resp.text}, ensure_ascii=False)

        data = resp.json()
        if data.get("code") != 0:
            return json.dumps({"error": f"Feishu error: {data.get('msg')}", "code": data.get("code")}, ensure_ascii=False)

        records = data.get("data", {}).get("items", [])
        return json.dumps({
            "records": records,
            "total": len(records),
            "debug": {"table_name": _table_name, "table_id": table_id, "filter_body": body}
        }, ensure_ascii=False, indent=2)

    async def list_fields(self, table_name="") -> str:
        """
        仅供诊断使用：列出某张表的所有字段名。如果查询报错字段不存在，可用此工具排查。
        :param table_name: 表显示名称，不传则使用默认值
        """
        if not self.valves.app_id or not self.valves.app_secret:
            return json.dumps({"error": "Please configure app_id and app_secret"}, ensure_ascii=False)
        token = self._get_token()
        app_token = self.valves.default_app_token
        if not app_token:
            return json.dumps({"error": "Please configure default_app_token"}, ensure_ascii=False)
        _table_name = table_name.strip() or self.valves.default_table_name
        tables = self._list_tables(token, app_token)
        table_id = self._resolve_table_id(tables, _table_name)
        if not table_id:
            return json.dumps({"error": "Table not found"}, ensure_ascii=False)
        field_map = self._get_fields(token, app_token, table_id)
        return json.dumps({
            "table_name": _table_name,
            "fields": [{"name": name, "field_id": fid} for name, fid in field_map.values()]
        }, ensure_ascii=False, indent=2)
```

## Valves 配置说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `app_id` | 是 | 飞书开放平台应用的 App ID |
| `app_secret` | 是 | 飞书开放平台应用的 App Secret |
| `base_url` | 否 | 默认 `https://open.feishu.cn`，企业私有化部署时修改 |
| `default_app_token` | 是 | 多维表格文档的 app_token（飞书文档地址栏 `base/` 后面的 ID） |
| `default_table_name` | 是 | 默认数据表显示名称，如 `人才盘点数据源` |

## 飞书应用权限要求

在[飞书开放平台](https://open.feishu.cn/app) → 权限管理，开启：
- `bitable:app:readonly` — 读取多维表格
- `bitable:record:readonly` — 读取记录
- `drive:drive:readonly` — 读取云文档（部分场景需要）

开启后需**发布版本**才能生效。

## 关键踩坑记录

### 1. GET filter 参数编码问题（InvalidFilter 1254018）

最初使用 GET `/records?filter=...`，filter 作为 URL query string 传递。飞书要求 filter 是 JSON 字符串，URL 编码后格式极易出错，返回 `InvalidFilter`。

**解决**: 统一改用 **POST `/records/search`**，filter 放在 JSON body 中，彻底规避编码问题。

### 2. LLM 偷懒只调 `list_tables`

OpenWebUI 会暴露 Tool 类中所有 `async def` 方法。LLM 看到 `list_tables`（只返回表名）和 `query_employee_records`（返回数据），倾向于选"简单"的 `list_tables`，拿到表名后就编造回复说"没有具体数据"。

**解决**: **删除 `list_tables` 函数**。LLM 没得选，只能直接调用 `query_employee_records`。

### 3. Valves 配置保存与代码保存是独立操作

前端"保存代码"和"保存 Valves"是两个不同的按钮。如果只保存代码没保存 Valves，运行时会报 Pydantic validation error（`app_id Field required`）。

**解决**: 代码保存后，必须到 Tool 详情页单独点击 Valves 区域的"保存配置"，并刷新页面确认值还在。

### 4. 字段缓存污染

最初加了 `_table_cache` 和 `_field_cache`（5 分钟 TTL）。某次查询飞书返回异常数据后，脏缓存持续 5 分钟，导致后续查询报"仅包含文本字段"。

**解决**: **彻底删除缓存机制**。每次查询实时请求飞书 API，数据量不大，性能可接受。

### 5. 模型不支持 Function Calling

如果对话使用的模型不支持 tool calling（如部分本地小模型），LLM 看到 Tool 定义也不会调用，直接编回复。

**解决**: 使用支持 function calling 的模型：GPT-4o、Claude 3.5/4、DeepSeek-V3、Qwen-Max 等。

## 使用示例

**用户输入**:
```
查询人才盘点数据源中部门是开发部的员工
```

**LLM 调用**:
```python
query_employee_records(
    table_name="人才盘点数据源",
    filter_formula='CurrentValue["部门"] == "开发部"'
)
```

**Tool 内部解析**:
```python
# 原始 filter
CurrentValue["部门"] == "开发部"

# 解析后 JSON body
{"filter": {"conjunction": "and", "conditions": [{"field_name": "部门", "operator": "is", "value": ["开发部"]}]}}
```

**返回示例**:
```json
{
  "records": [
    {"fields": {"姓名": [{"text": "张三"}], "部门": [{"text": "开发部"}], "绩效等级": "B", "潜力评分": 2}},
    {"fields": {"姓名": [{"text": "李四"}], "部门": [{"text": "开发部"}], "绩效等级": "B", "潜力评分": 4}},
    {"fields": {"姓名": [{"text": "王五"}], "部门": [{"text": "开发部"}], "绩效等级": "A", "潜力评分": 6}}
  ],
  "total": 3
}
```
