"""
Expert Wiki Module

每个 Expert 拥有独立的 Wiki 空间，包含：
- raw/ - 原始资料
- wiki/ - 编译后的 Wiki 页面
- index.md - 主题索引

这个模块负责 Wiki 的存储、召回和健康检查。
"""

import asyncio
import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Optional

from open_webui.env import DATA_DIR

log = logging.getLogger(__name__)


class WikiPage:
    """Wiki 页面数据模型"""

    def __init__(
        self,
        path: str,
        title: str,
        content: str,
        page_type: str = "topic",
        sources: list[str] = None,
        links: list[str] = None,
    ):
        self.path = path
        self.title = title
        self.content = content
        self.page_type = page_type
        self.sources = sources or []
        self.links = links or []

    def to_dict(self):
        return {
            "path": self.path,
            "title": self.title,
            "content": self.content,
            "page_type": self.page_type,
            "sources": self.sources,
            "links": self.links,
        }


class WikiIndex:
    """Wiki 索引结构"""

    def __init__(self, wiki_root: Path):
        self.wiki_root = wiki_root
        self.index_path = wiki_root / "index.md"
        self.topics = []  # list of {title, path, summary}

    def load(self) -> bool:
        """从 index.md 加载索引"""
        if not self.index_path.exists():
            return False

        try:
            content = self.index_path.read_text(encoding="utf-8")
            # 简单的解析：提取 ## 标题 和对应的路径
            lines = content.split("\n")
            for line in lines:
                # 匹配 ## 标题 或 ### 标题
                match = re.match(r"^#{2,3}\s+\[(.+?)\]\((.+?)\)", line)
                if match:
                    title = match.group(1)
                    path = match.group(2)
                    self.topics.append({"title": title, "path": path})
            return True
        except Exception as e:
            log.error(f"Failed to load wiki index: {e}")
            return False

    def add_topic(self, title: str, path: str, summary: str = ""):
        """添加主题到索引"""
        self.topics.append({"title": title, "path": path, "summary": summary})

    def save(self):
        """保存索引到 index.md"""
        lines = ["# Wiki Index\n\n"]

        # 按类型分组
        by_type = {}
        for topic in self.topics:
            page_type = Path(topic["path"]).parent.name
            if page_type not in by_type:
                by_type[page_type] = []
            by_type[page_type].append(topic)

        for page_type, topics in by_type.items():
            lines.append(f"## {page_type}\n\n")
            for topic in topics:
                title = topic["title"]
                path = topic["path"]
                summary = topic.get("summary", "")
                lines.append(f"- [{title}]({path})")
                if summary:
                    lines.append(f"  - {summary}")
            lines.append("")

        self.index_path.write_text("\n".join(lines), encoding="utf-8")

    def match(self, query: str) -> list[dict]:
        """根据 query 匹配相关主题"""
        query_lower = query.lower()
        matches = []

        for topic in self.topics:
            title = topic["title"].lower()
            # 简单匹配：query 中的词出现在 title 中
            if any(word in title for word in query_lower.split()):
                matches.append(topic)

        return matches


class WikiRetriever:
    """运行时从 Wiki 召回知识"""

    def __init__(self, wiki_root: str):
        self.wiki_root = Path(wiki_root)

    @property
    def raw_dir(self) -> Path:
        return self.wiki_root / "raw"

    @property
    def wiki_dir(self) -> Path:
        return self.wiki_root / "wiki"

    @property
    def index(self) -> WikiIndex:
        return WikiIndex(self.wiki_root)

    def read_wiki_page(self, path: str) -> Optional[str]:
        """读取单个 Wiki 页内容"""
        page_path = self.wiki_root / path
        if not page_path.exists():
            return None

        try:
            return page_path.read_text(encoding="utf-8")
        except Exception as e:
            log.error(f"Failed to read wiki page {path}: {e}")
            return None

    def read_page_content(self, page_path: Path) -> Optional[str]:
        """读取 Wiki 页面的实际内容（跳过 frontmatter）"""
        if not page_path.exists():
            return None

        try:
            content = page_path.read_text(encoding="utf-8")
            # 跳过 YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2].strip()
            return content
        except Exception as e:
            log.error(f"Failed to read page content {page_path}: {e}")
            return None

    def list_wiki_pages(self, subdir: str = "") -> list[WikiPage]:
        """列出 Wiki 目录下的所有页面"""
        pages = []
        target_dir = self.wiki_dir / subdir if subdir else self.wiki_dir

        if not target_dir.exists():
            return pages

        for path in target_dir.rglob("*.md"):
            relative_path = path.relative_to(self.wiki_root)
            content = self.read_page_content(path)
            if content:
                # 从文件名或内容提取标题
                title = path.stem.replace("-", " ").replace("_", " ").title()
                # 尝试从 content 提取标题
                for line in content.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

                pages.append(
                    WikiPage(
                        path=str(relative_path),
                        title=title,
                        content=content,
                        page_type=path.parent.name,
                    )
                )

        return pages

    async def retrieve(
        self,
        query: str,
        pinned_pages: list[str] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        混合召回策略：
        1. pinned_pages 直接读 wiki 页（最高优先级）
        2. index.md 匹配找相关主题
        3. wiki/*.md 内容查询
        """
        results = []

        # 1. 固定页注入
        if pinned_pages:
            for page_path in pinned_pages:
                content = self.read_wiki_page(page_path)
                if content:
                    results.append(
                        {
                            "content": content,
                            "source": page_path,
                            "priority": 1,
                            "type": "pinned",
                        }
                    )

        # 2. 主题索引召回
        index = WikiIndex(self.wiki_root)
        if index.load():
            matched_topics = index.match(query)
            for topic in matched_topics[:3]:
                content = self.read_wiki_page(topic["path"])
                if content:
                    results.append(
                        {
                            "content": content,
                            "source": topic["path"],
                            "priority": 2,
                            "type": "index",
                        }
                    )

        # 3. Wiki 内容搜索（简单关键词匹配）
        all_pages = self.list_wiki_pages()
        query_words = query.lower().split()

        for page in all_pages:
            # 跳过已经添加的页面
            if any(r["source"] == page.path for r in results):
                continue

            # 简单匹配：query 词出现在 title 或 content 中
            score = 0
            title_lower = page.title.lower()
            content_lower = page.content.lower()

            for word in query_words:
                if word in title_lower:
                    score += 2
                if word in content_lower:
                    score += 1

            if score > 0:
                results.append(
                    {
                        "content": page.content[:2000],  # 限制长度
                        "source": page.path,
                        "priority": 3,
                        "type": "search",
                        "score": score,
                    }
                )

        # 按优先级排序
        results.sort(key=lambda x: (x["priority"], -x.get("score", 0)))

        return results[:top_k]

    def assemble_context(self, retrieved: list[dict]) -> str:
        """组装召回内容为 context 字符串"""
        if not retrieved:
            return ""

        parts = ["# Retrieved Knowledge\n\n"]

        for item in retrieved:
            source = item["source"]
            content = item["content"]
            parts.append(f"## From: {source}\n\n{content}\n\n")

        return "".join(parts)


class WikiHealthChecker:
    """Wiki 健康检查"""

    def __init__(self, wiki_root: str):
        self.wiki_root = Path(wiki_root)
        self.wiki_dir = self.wiki_root / "wiki"
        self.index_path = self.wiki_root / "index.md"

    def _get_all_wiki_pages(self) -> list[Path]:
        """获取所有 wiki 页面路径"""
        if not self.wiki_dir.exists():
            return []
        return list(self.wiki_dir.rglob("*.md"))

    def _extract_wikilinks(self, content: str) -> list[str]:
        """从 content 中提取 [[wikilink]] 格式的链接"""
        return re.findall(r"\[\[(.+?)\]\]", content)

    def _resolve_wikilink(self, link: str) -> Path:
        """解析 wikilink 为实际文件路径"""
        # 移除 .md 后缀
        link_path = link.replace(".md", "").replace(" ", "-").lower()
        return self.wiki_dir / f"{link_path}.md"

    async def check_all(self) -> dict:
        """执行所有健康检查"""
        issues = []

        # 1. 孤岛页检测（无入链的页面）
        orphan_pages = await self._find_orphan_pages()
        if orphan_pages:
            issues.append(
                {"rule_id": "orphan-page", "severity": "medium", "pages": orphan_pages}
            )

        # 2. 重复页检测（内容高度相似）
        duplicate_pages = await self._find_duplicate_pages()
        if duplicate_pages:
            issues.append(
                {
                    "rule_id": "duplicate-page",
                    "severity": "low",
                    "pages": duplicate_pages,
                }
            )

        # 3. 断链检测（指向不存在的页面）
        broken_links = await self._find_broken_links()
        if broken_links:
            issues.append(
                {"rule_id": "broken-link", "severity": "high", "links": broken_links}
            )

        return {
            "wiki_root": str(self.wiki_root),
            "total_pages": len(self._get_all_wiki_pages()),
            "issues": issues,
        }

    async def _find_orphan_pages(self) -> list[str]:
        """找出无入链的孤立 Wiki 页"""
        all_pages = {p.relative_to(self.wiki_dir) for p in self._get_all_wiki_pages()}
        pages_that_are_linked = set()

        for page_path in self._get_all_wiki_pages():
            content = page_path.read_text(encoding="utf-8")
            for link in self._extract_wikilinks(content):
                resolved = self._resolve_wikilink(link)
                if resolved.is_absolute():
                    resolved = resolved.relative_to(self.wiki_dir)
                pages_that_are_linked.add(resolved)

        # 找出没有被链接的页面
        orphans = []
        for page in all_pages:
            if page not in pages_that_are_linked:
                orphans.append(str(page))
        return orphans

    async def _find_duplicate_pages(self) -> list[str]:
        """找出内容高度重复的页面（简单实现：文件名相似）"""
        pages = self._get_all_wiki_pages()
        duplicates = []

        # 简单实现：检查文件名相似的页面
        names = []
        for p in pages:
            name = p.stem.lower().replace("-", " ").replace("_", " ")
            names.append((p, name))

        for i, (p1, n1) in enumerate(names):
            for p2, n2 in names[i + 1 :]:
                # 如果 stem 完全相同
                if p1.stem == p2.stem:
                    duplicates.append(str(p1))
                    duplicates.append(str(p2))

        return list(set(duplicates))

    async def _find_broken_links(self) -> list[dict]:
        """找出指向不存在页面的链接"""
        broken = []

        for page_path in self._get_all_wiki_pages():
            content = page_path.read_text(encoding="utf-8")
            for link in self._extract_wikilinks(content):
                resolved = self._resolve_wikilink(link)
                if not resolved.exists():
                    broken.append(
                        {"from": str(page_path.relative_to(self.wiki_root)), "link": link}
                    )

        return broken


def get_expert_wiki_root(expert_id: str) -> Path:
    """获取 Expert 的 Wiki 根目录"""
    return DATA_DIR / "experts" / expert_id


def ensure_wiki_structure(expert_id: str) -> Path:
    """确保 Expert 的 Wiki 目录结构存在"""
    wiki_root = get_expert_wiki_root(expert_id)

    dirs = [
        "raw/articles",
        "raw/pdfs",
        "raw/notes",
        "raw/assets",
        "wiki/entities",
        "wiki/topics",
        "wiki/sources",
        "wiki/synthesis/sessions",
        "wiki/comparison",
        "wiki/query",
    ]

    for d in dirs:
        (wiki_root / d).mkdir(parents=True, exist_ok=True)

    # 确保必要文件存在
    for fname in ["index.md", "log.md", "purpose.md"]:
        fpath = wiki_root / fname
        if not fpath.exists():
            fpath.write_text("", encoding="utf-8")

    return wiki_root