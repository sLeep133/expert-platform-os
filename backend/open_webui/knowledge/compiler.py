"""
WikiCompiler Module

封装 llm-wiki 编译逻辑，实现两步式编译：
- Step 1: LLM 分析（理解原始资料）
- Step 2: LLM 生成（产出结构化 Wiki）

这个模块负责将原始资料编译为 Wiki 页面。
"""

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

import aiohttp
from pydantic import BaseModel

from open_webui.config import DATA_DIR
from open_webui.knowledge.llm import call_llm_simple

log = logging.getLogger(__name__)


async def call_llm_chat(
    prompt: str,
    system: Optional[str] = None,
    model: str = None,
    base_url: str = None,
    api_key: str = None,
) -> str:
    """
    调用 LLM 进行聊天补全（使用 open-webui 已配置的大模型）

    Args:
        prompt: 用户 prompt
        system: 系统提示词
        model: 模型名称（可选）
        base_url: API 地址（忽略，使用已配置）
        api_key: API Key（忽略）

    Returns:
        LLM 生成的文本内容
    """
    return await call_llm_simple(prompt, system=system, model=model)


class CompileResult(BaseModel):
    """编译结果"""

    expert_id: str
    status: str  # "completed", "failed", "running"
    pages: list[dict] = []
    errors: list[str] = []
    duration: float = 0


class WikiCompiler:
    """
    封装 llm-wiki 编译逻辑

    使用两步式编译：
    1. Step 1: LLM 分析原始资料 → 结构化分析结果
    2. Step 2: LLM 根据分析结果生成 Wiki 页面
    """

    def __init__(self, expert_id: str, llm_config: Optional[dict] = None):
        self.expert_id = expert_id
        self.llm_config = llm_config or {}
        self.wiki_root = DATA_DIR / "experts" / expert_id
        self.raw_dir = self.wiki_root / "raw"
        self.wiki_dir = self.wiki_root / "wiki"
        self._cache_file = self.wiki_root / ".wiki-cache.json"

    def _load_cache(self) -> dict:
        """加载增量缓存"""
        if self._cache_file.exists():
            try:
                import json

                return json.loads(self._cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"version": 1, "entries": {}}

    def _save_cache(self, cache: dict):
        """保存增量缓存"""
        try:
            import json

            self._cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log.error(f"Failed to save cache: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件 hash"""
        hasher = hashlib.sha256()
        hasher.update(file_path.read_bytes())
        return hasher.hexdigest()

    async def compile_file(
        self, file_path: str, auto_trigger: bool = True
    ) -> CompileResult:
        """
        编译单个文件为 Wiki 页

        Args:
            file_path: 原始文件路径
            auto_trigger: 是否自动触发编译

        Returns:
            CompileResult
        """
        start_time = time.time()
        file_path = Path(file_path)

        if not file_path.exists():
            return CompileResult(
                expert_id=self.expert_id,
                status="failed",
                errors=[f"File not found: {file_path}"],
                duration=time.time() - start_time,
            )

        # 检查增量缓存
        cache = self._load_cache()
        file_hash = self._get_file_hash(file_path)

        if file_hash in cache.get("entries", {}):
            log.info(f"File {file_path.name} not changed, skipping compile")
            return CompileResult(
                expert_id=self.expert_id,
                status="completed",
                pages=[],
                duration=time.time() - start_time,
            )

        try:
            # Step 1: 根据文件类型读取内容
            content = self._read_file_content(file_path)

            # Step 2: 分析内容
            analysis = await self._step1_analyze(content, file_path.name)

            # Step 3: 生成 Wiki 页面
            pages = await self._step2_generate(analysis, file_path)

            # 更新缓存
            cache["entries"][file_hash] = {
                "file": str(file_path),
                "compiled_at": int(time.time()),
                "pages": len(pages),
            }
            self._save_cache(cache)

            return CompileResult(
                expert_id=self.expert_id,
                status="completed",
                pages=pages,
                duration=time.time() - start_time,
            )

        except Exception as e:
            log.exception(f"Failed to compile {file_path}: {e}")
            return CompileResult(
                expert_id=self.expert_id,
                status="failed",
                errors=[str(e)],
                duration=time.time() - start_time,
            )

    def _read_file_content(self, file_path: Path) -> str:
        """根据文件类型读取内容"""
        suffix = file_path.suffix.lower()

        # PDF 文件
        if suffix == '.pdf':
            return self._read_pdf(file_path)

        # Word 文档
        if suffix in ['.docx', '.doc']:
            return self._read_docx(file_path)

        # Markdown / 纯文本文件 - 直接读取
        if suffix in ['.md', '.txt', '.text']:
            return file_path.read_text(encoding="utf-8", errors="ignore")

        # 代码文件
        if suffix in [
            '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.h',
            '.rb', '.php', '.swift', '.kt', '.scala', '.sql', '.sh', '.bash',
            '.json', '.yaml', '.yml', '.toml', '.xml', '.html', '.css',
        ]:
            return file_path.read_text(encoding="utf-8", errors="ignore")

        # Excel 文件
        if suffix in ['.xlsx', '.xls', '.csv']:
            return self._read_excel(file_path)

        # 默认：尝试读取文本，失败则返回空
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return f"[无法读取 {suffix} 格式的文件内容]"

    def _read_pdf(self, file_path: Path) -> str:
        """读取 PDF 文件内容"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n".join(text_parts)
        except Exception as e:
            log.error(f"Failed to read PDF {file_path}: {e}")
            return f"[PDF 文件读取失败: {e}]"

    def _read_docx(self, file_path: Path) -> str:
        """读取 Word 文档内容"""
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            log.error(f"Failed to read docx {file_path}: {e}")
            return f"[Word 文档读取失败: {e}]"

    def _read_excel(self, file_path: Path) -> str:
        """读取 Excel/CSV 文件内容"""
        try:
            import pandas as pd
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            return df.to_string()
        except Exception as e:
            log.error(f"Failed to read excel {file_path}: {e}")
            return f"[Excel 文件读取失败: {e}]"
            return CompileResult(
                expert_id=self.expert_id,
                status="failed",
                errors=[str(e)],
                duration=time.time() - start_time,
            )

    async def compile_all(self) -> CompileResult:
        """编译 raw 目录下所有文件"""
        start_time = time.time()
        all_pages = []
        errors = []

        if not self.raw_dir.exists():
            return CompileResult(
                expert_id=self.expert_id,
                status="completed",
                pages=[],
                duration=time.time() - start_time,
            )

        # 遍历 raw 目录下所有文件
        for file_path in self.raw_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                result = await self.compile_file(str(file_path))
                if result.status == "failed":
                    errors.extend(result.errors)
                all_pages.extend(result.pages)

        return CompileResult(
            expert_id=self.expert_id,
            status="completed" if not errors else "failed" if errors else "completed",
            pages=all_pages,
            errors=errors,
            duration=time.time() - start_time,
        )

    async def _step1_analyze(
        self, content: str, filename: str
    ) -> dict:
        """
        Step 1: LLM 分析原始资料

        返回结构化分析结果，包含：
        - key_entities: 关键实体
        - key_concepts: 关键概念
        - topics: 主题
        - relationships: 关系
        """
        prompt = f"""请分析以下文档，提取结构化信息。

文档内容：
{content[:4000]}

请以 JSON 格式返回分析结果，包含以下字段：
- summary: 文档摘要（100字以内）
- key_entities: 关键实体列表（人名、地点、机构、技术名词等，最多10个）
- key_concepts: 关键概念列表（最重要的核心概念，最多10个）
- topics: 主题标签列表（3-5个主题）
- suggested_page_type: 建议的页面类型（topic/entity/source/synthesis）
- relationships: 关键关系描述（可选，描述实体之间的关系）

直接返回 JSON，不要有额外解释。"""

        try:
            result = await call_llm_chat(
                prompt=prompt,
                system="你是一个文档分析助手，擅长提取关键信息。请严格按照 JSON 格式返回结果。",
                model=self.llm_config.get("model", "deepseek-r1:14b"),
            )

            # 尝试解析 JSON
            try:
                # 清理可能存在的 markdown 代码块
                if result.startswith("```"):
                    lines = result.split("\n")
                    result = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                analysis = json.loads(result)
                return {
                    "filename": filename,
                    "summary": analysis.get("summary", content[:500]),
                    "key_entities": analysis.get("key_entities", []),
                    "key_concepts": analysis.get("key_concepts", []),
                    "topics": analysis.get("topics", []),
                    "suggested_page_type": analysis.get("suggested_page_type", "topic"),
                }
            except json.JSONDecodeError:
                # 如果无法解析 JSON，返回基本分析
                log.warning(f"Failed to parse LLM response as JSON, using fallback: {result[:100]}")
                return {
                    "filename": filename,
                    "summary": content[:500],
                    "key_entities": [],
                    "key_concepts": [],
                    "topics": [],
                    "suggested_page_type": "topic",
                }
        except Exception as e:
            log.error(f"Step 1 analysis failed: {e}")
            return {
                "filename": filename,
                "summary": content[:500],
                "key_entities": [],
                "key_concepts": [],
                "topics": [],
                "suggested_page_type": "topic",
            }

    async def _step2_generate(self, analysis: dict, source_file: Path) -> list[dict]:
        """
        Step 2: LLM 生成 Wiki 页面

        根据分析结果生成结构化 Wiki 页
        """
        pages = []
        title = source_file.stem.replace("-", " ").replace("_", " ").title()
        page_type = analysis.get("suggested_page_type", "topic")

        # 调用 LLM 生成 Wiki 页面内容
        prompt = f"""请根据以下分析结果，为文档生成一个结构化的 Wiki 页面。

文档信息：
- 原始文件名：{source_file.name}
- 分析摘要：{analysis.get("summary", "")}

关键概念：
{chr(10).join(f"- {c}" for c in analysis.get("key_concepts", []))}

关键实体：
{chr(10).join(f"- {e}" for e in analysis.get("key_entities", []))}

主题标签：{", ".join(analysis.get("topics", []))}

请生成一个 Markdown 格式的 Wiki 页面，包含：
1. 标题（使用 # 标题）
2. 概述（基于 summary）
3. 关键概念详细说明（使用 ## 小节）
4. 关键实体列表（如有）
5. 相关主题（如有）

页面类型：{page_type}

请直接返回 Markdown 内容，不要有额外的解释。"""

        try:
            page_content = await call_llm_chat(
                prompt=prompt,
                system="你是一个专业的 Wiki 编辑，擅长生成结构化、可读性强的文档内容。使用中文回复。",
                model=self.llm_config.get("model", "deepseek-r1:14b"),
            )

            # 如果返回为空或失败，使用 fallback
            if not page_content or len(page_content) < 50:
                page_content = self._generate_fallback_page(title, analysis, source_file, page_type)
        except Exception as e:
            log.error(f"Step 2 generation failed: {e}")
            page_content = self._generate_fallback_page(title, analysis, source_file, page_type)

        # 确保 frontmatter 存在
        if not page_content.startswith("---"):
            page_content = f"""---
title: {title}
type: {page_type}
sources:
  - {source_file.name}
---

{page_content}"""

        # 确定输出路径
        output_dir = self.wiki_dir / page_type
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{source_file.stem}.md"
        output_path.write_text(page_content, encoding="utf-8")

        pages.append(
            {
                "path": str(output_path.relative_to(self.wiki_root)),
                "title": title,
                "type": page_type,
            }
        )

        # 更新 index.md
        await self._update_index(pages)

        return pages

    def _generate_fallback_page(
        self, title: str, analysis: dict, source_file: Path, page_type: str
    ) -> str:
        """当 LLM 生成失败时生成占位符页面"""
        return f"""---
title: {title}
type: {page_type}
sources:
  - {source_file.name}
---

# {title}

{analysis.get("summary", "")}

## Key Concepts

{chr(10).join(f"- {c}" for c in analysis.get("key_concepts", []))}

## Key Entities

{chr(10).join(f"- {e}" for e in analysis.get("key_entities", []))}

## Topics

{chr(10).join(f"- {t}" for t in analysis.get("topics", []))}
"""

    async def _update_index(self, new_pages: list[dict]):
        """更新 index.md 主题索引"""
        index_path = self.wiki_root / "index.md"
        existing_topics = []

        # 读取现有 index
        if index_path.exists():
            content = index_path.read_text(encoding="utf-8")
            # 简单解析现有主题
            import re

            for match in re.findall(r"- \[(.+?)\]\((.+?)\)", content):
                title, path = match
                existing_topics.append({"title": title, "path": path})

        # 添加新页面
        for page in new_pages:
            path = page["path"]
            title = page["title"]
            if not any(t["path"] == path for t in existing_topics):
                existing_topics.append({"title": title, "path": path})

        # 写入更新的 index
        lines = ["# Wiki Index\n\n"]
        for topic in existing_topics:
            lines.append(f"- [{topic['title']}]({topic['path']})")
        lines.append("")

        index_path.write_text("\n".join(lines), encoding="utf-8")

    async def trigger_compile(self, file_path: str = None):
        """触发编译（供 API 调用）"""
        if file_path:
            return await self.compile_file(file_path)
        return await self.compile_all()


async def compile_expert_wiki(expert_id: str, file_path: str = None) -> CompileResult:
    """
    便捷函数：编译指定 Expert 的 Wiki

    Args:
        expert_id: Expert ID
        file_path: 可选，指定单个文件路径

    Returns:
        CompileResult
    """
    compiler = WikiCompiler(expert_id)
    if file_path:
        return await compiler.compile_file(file_path)
    return await compiler.compile_all()