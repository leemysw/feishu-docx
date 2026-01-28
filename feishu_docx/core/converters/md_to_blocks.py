# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：md_to_blocks.py
# @Date   ：2026/01/28 12:40
# @Author ：leemysw
# 2026/01/18 15:40   Create
# 2026/01/28 10:20   Add image/table/math support
# 2026/01/28 12:20   Fix equation block schema and Å mapping
# 2026/01/28 12:30   Fix \\text{..._...} subscript rendering
# 2026/01/28 12:40   Fix mistune table parsing and cell content
# =====================================================
"""
Markdown → 飞书 Block 转换器

[INPUT]: 依赖 mistune 的 Markdown 解析器
[OUTPUT]: 对外提供 MarkdownToBlocks 类，将 Markdown 转换为飞书 Block 结构
[POS]: converters 模块的核心转换器
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import mistune
from mistune.plugins.math import math as math_plugin
from mistune.plugins.table import table as table_plugin


class MarkdownToBlocks:
    """
    Markdown → 飞书 Block 转换器

    使用 mistune 解析 Markdown，转换为飞书文档 Block 结构。
    支持：标题、段落、列表、代码块、引用、分割线、文本样式。
    """

    # Block 类型映射
    BLOCK_TYPE_TEXT = 2
    BLOCK_TYPE_HEADING1 = 3
    BLOCK_TYPE_HEADING2 = 4
    BLOCK_TYPE_HEADING3 = 5
    BLOCK_TYPE_HEADING4 = 6
    BLOCK_TYPE_HEADING5 = 7
    BLOCK_TYPE_HEADING6 = 8
    BLOCK_TYPE_HEADING7 = 9
    BLOCK_TYPE_HEADING8 = 10
    BLOCK_TYPE_HEADING9 = 11
    BLOCK_TYPE_BULLET = 12
    BLOCK_TYPE_ORDERED = 13
    BLOCK_TYPE_CODE = 14
    BLOCK_TYPE_QUOTE = 15
    BLOCK_TYPE_TODO = 17
    BLOCK_TYPE_DIVIDER = 22
    BLOCK_TYPE_IMAGE = 27
    BLOCK_TYPE_TABLE = 31
    BLOCK_TYPE_TABLE_CELL = 32

    # 代码语言映射
    LANGUAGE_MAP = {
        "python": 49,
        "javascript": 22,
        "typescript": 75,
        "java": 21,
        "go": 13,
        "rust": 56,
        "c": 5,
        "cpp": 7,
        "csharp": 8,
        "ruby": 55,
        "php": 46,
        "swift": 68,
        "kotlin": 25,
        "sql": 64,
        "shell": 61,
        "bash": 3,
        "json": 23,
        "yaml": 81,
        "xml": 79,
        "html": 17,
        "css": 9,
        "markdown": 34,
    }

    def __init__(self):
        """初始化转换器"""
        self._md = mistune.create_markdown(
            renderer=None,
            plugins=[table_plugin, math_plugin],
        )
        self.image_paths: List[str] = []

    def convert(self, markdown_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        将 Markdown 文本转换为飞书 Block 列表

        Args:
            markdown_text: Markdown 文本

        Returns:
            (Blocks 列表, 图片路径列表)
        """
        self.image_paths = []
        tokens = self._md.parse(markdown_text)
        if isinstance(tokens, tuple):
            tokens = tokens[0]

        blocks = []
        for token in tokens:
            block = self._convert_token(token)
            if not block:
                continue

            new_blocks = block if isinstance(block, list) else [block]
            for b in new_blocks:
                if not isinstance(b, dict):
                    continue
                bt = b.get("block_type")
                if bt in [
                    self.BLOCK_TYPE_TEXT,
                    self.BLOCK_TYPE_HEADING1,
                    self.BLOCK_TYPE_HEADING2,
                    self.BLOCK_TYPE_HEADING3,
                    self.BLOCK_TYPE_HEADING4,
                    self.BLOCK_TYPE_HEADING5,
                    self.BLOCK_TYPE_HEADING6,
                    self.BLOCK_TYPE_HEADING7,
                    self.BLOCK_TYPE_HEADING8,
                    self.BLOCK_TYPE_HEADING9,
                    self.BLOCK_TYPE_BULLET,
                    self.BLOCK_TYPE_ORDERED,
                    self.BLOCK_TYPE_QUOTE,
                    self.BLOCK_TYPE_TODO,
                ]:
                    payload_key = next((k for k in b.keys() if k != "block_type"), None)
                    if payload_key and not b[payload_key].get("elements"):
                        continue
                blocks.append(b)

        return blocks, self.image_paths

    def convert_file(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        读取 Markdown 文件并转换

        Args:
            file_path: 文件路径

        Returns:
            (Blocks 列表, 图片路径列表)
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return self.convert(f.read())

    @staticmethod
    def _is_remote_url(url: str) -> bool:
        """判断是否为远程 URL（不可直接上传）"""
        return bool(re.match(r"^(?:https?:)?//|^data:", url.strip(), re.IGNORECASE))

    def _convert_token(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """转换单个 token"""
        token_type = token.get("type")

        if token_type == "heading":
            return self._make_heading(token)
        elif token_type == "paragraph":
            return self._make_paragraph(token)
        elif token_type == "list":
            return self._make_list(token)
        elif token_type == "block_code":
            return self._make_code_block(token)
        elif token_type == "block_quote":
            return self._make_quote(token)
        elif token_type == "thematic_break":
            return self._make_divider()
        elif token_type == "block_math":
            return self._make_equation(token)
        elif token_type == "math":
            return self._make_equation(token)
        elif token_type == "table":
            return self._make_table(token)
        elif token_type == "image":
            return self._make_image(token)

        return None

    def _make_heading(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """创建标题 Block"""
        level = token.get("attrs", {}).get("level", 1)
        level = min(max(level, 1), 6)  # 限制 1-6
        block_type = self.BLOCK_TYPE_HEADING1 + level - 1

        elements = self._extract_text_elements(token.get("children", []))

        heading_key = f"heading{level}"
        return {
            "block_type": block_type,
            heading_key: {"elements": elements},
        }

    def _make_paragraph(self, token: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建段落 Block (支持中途插入图片并分割)"""
        children = token.get("children", [])
        blocks = []
        current_elements = []

        for child in children:
            if child.get("type") == "image":
                if current_elements:
                    blocks.append({
                        "block_type": self.BLOCK_TYPE_TEXT,
                        "text": {"elements": current_elements},
                    })
                    current_elements = []

                img_block = self._make_image(child)
                if img_block:
                    blocks.append(img_block)
            else:
                current_elements.extend(self._extract_text_elements([child]))

        if current_elements:
            blocks.append({
                "block_type": self.BLOCK_TYPE_TEXT,
                "text": {"elements": current_elements},
            })

        return blocks

    def _make_image(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理图片"""
        url = token.get("attrs", {}).get("url", "")
        if not url:
            return None

        if self._is_remote_url(url):
            return {
                "block_type": self.BLOCK_TYPE_TEXT,
                "text": {
                    "elements": [
                        {
                            "text_run": {
                                "content": f"![Image]({url})",
                                "text_element_style": {},
                            }
                        }
                    ]
                },
            }

        self.image_paths.append(url)
        return {
            "block_type": self.BLOCK_TYPE_IMAGE,
            "image": {},
        }

    def _make_list(self, token: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建列表 Block（每个列表项一个 Block）"""
        ordered = token.get("attrs", {}).get("ordered", False)
        block_type = self.BLOCK_TYPE_ORDERED if ordered else self.BLOCK_TYPE_BULLET
        list_key = "ordered" if ordered else "bullet"

        blocks = []
        for item in token.get("children", []):
            if item.get("type") == "list_item":
                elements = []
                image_blocks: List[Dict[str, Any]] = []
                for child in item.get("children", []):
                    if child.get("type") in ["paragraph", "block_text"]:
                        for sub in child.get("children", []):
                            if sub.get("type") == "image":
                                img_block = self._make_image(sub)
                                if img_block:
                                    image_blocks.append(img_block)
                            else:
                                elements.extend(self._extract_text_elements([sub]))

                if elements:
                    blocks.append({
                        "block_type": block_type,
                        list_key: {"elements": elements},
                    })
                if image_blocks:
                    blocks.extend(image_blocks)

        return blocks

    def _make_code_block(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """创建代码块 Block"""
        raw_text = token.get("raw", "")
        lang = token.get("attrs", {}).get("info", "").lower()
        lang_code = self.LANGUAGE_MAP.get(lang, 1)  # 1 = PlainText

        return {
            "block_type": self.BLOCK_TYPE_CODE,
            "code": {
                "elements": [{"text_run": {"content": raw_text}}],
                "style": {"language": lang_code},
            },
        }

    def _make_quote(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """创建引用 Block"""
        elements = []
        for child in token.get("children", []):
            if child.get("type") == "paragraph":
                elements.extend(
                    self._extract_text_elements(child.get("children", []))
                )

        return {
            "block_type": self.BLOCK_TYPE_QUOTE,
            "quote": {"elements": elements},
        }

    def _make_divider(self) -> Dict[str, Any]:
        """创建分割线 Block"""
        return {
            "block_type": self.BLOCK_TYPE_DIVIDER,
            "divider": {},
        }

    def _sanitize_latex(self, content: str) -> str:
        """飞书公式编辑器不支持部分命令，进行替换"""
        if not content:
            return ""
        content = re.sub(r"\\operatorname\s*{([^}]*)}", r"\\text{\1}", content)
        content = re.sub(r"\\tag\s*{([^}]*)}", r"(\1)", content)
        content = re.sub(
            r"\\text\s*{([^}]*)}",
            lambda m: (
                f"\\mathrm{{{m.group(1)}}}"
                if ("_" in m.group(1) or "^" in m.group(1))
                else m.group(0)
            ),
            content,
        )
        content = re.sub(
            r"\\mathring\s*{\s*\\mathrm\s*(?:{\s*A\s*}|A)\s*}",
            r"\\AA",
            content,
        )
        content = re.sub(r"\\mathring\s*{\s*A\s*}", r"\\AA", content)
        content = re.sub(r"\\mathring\s*{([^}]*)}", r"\1", content)
        return content

    def _make_equation(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建数学公式 Block"""
        content = token.get("attrs", {}).get("content", "") or token.get("raw", "").strip("$").strip()
        content = self._sanitize_latex(content)
        if not content:
            return None
        return {
            "block_type": self.BLOCK_TYPE_TEXT,
            "text": {
                "style": {"align": 2},
                "elements": [
                    {"equation": {"content": content}},
                ],
            },
        }

    def _make_table(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """创建表格 Block"""
        def table_cell_children(cell_children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """
            将 table_cell 的 inline children 转为可写入的 block children
            - 文字/链接/行内公式 -> Text block elements
            - 图片 -> Image block（必要时拆分前后文字）
            """
            blocks: List[Dict[str, Any]] = []
            inline_buffer: List[Dict[str, Any]] = []

            def flush_inline() -> None:
                nonlocal inline_buffer
                if not inline_buffer:
                    return
                elements = self._extract_text_elements(inline_buffer)
                blocks.append({
                    "block_type": self.BLOCK_TYPE_TEXT,
                    "text": {"elements": elements},
                })
                inline_buffer = []

            for child in cell_children:
                if child.get("type") == "image":
                    flush_inline()
                    img_block = self._make_image(child)
                    if img_block:
                        blocks.append(img_block)
                else:
                    inline_buffer.append(child)

            flush_inline()

            if not blocks:
                blocks.append({
                    "block_type": self.BLOCK_TYPE_TEXT,
                    "text": {"elements": []},
                })
            return blocks

        def normalize_rows(table_token: Dict[str, Any]) -> List[List[Dict[str, Any]]]:
            """
            兼容 mistune 的 table token 结构：
            - table_body: children 为 table_row -> children 为 table_cell
            - table_head: 可能直接是 table_cell 列表（单行表头），也可能是 table_row 列表
            """
            rows: List[List[Dict[str, Any]]] = []
            for part in table_token.get("children", []) or []:
                part_type = part.get("type")

                if part_type == "table_head":
                    head_children = part.get("children", []) or []
                    if not head_children:
                        continue
                    # mistune 3.2+ 可能将表头直接展开成 table_cell 列表（单行）
                    if all(c.get("type") == "table_cell" for c in head_children):
                        rows.append(head_children)
                        continue
                    # 兼容 table_row
                    for row in head_children:
                        if row.get("type") == "table_row":
                            rows.append(row.get("children", []) or [])
                        elif row.get("type") == "table_cell":
                            rows.append([row])

                if part_type == "table_body":
                    for row in part.get("children", []) or []:
                        if row.get("type") == "table_row":
                            rows.append(row.get("children", []) or [])
                        elif row.get("type") == "table_cell":
                            rows.append([row])

            return rows

        rows = normalize_rows(token)
        row_count = len(rows)
        col_count = max((len(r) for r in rows), default=0)

        cell_blocks: List[Dict[str, Any]] = []
        for r in range(row_count):
            row = rows[r]
            for c in range(col_count):
                cell_token = row[c] if c < len(row) else None
                cell_children_tokens = (cell_token or {}).get("children", []) if cell_token else []
                cell_blocks.append({
                    "block_type": self.BLOCK_TYPE_TABLE_CELL,
                    "table_cell": {},
                    "children": table_cell_children(cell_children_tokens),
                })

        return {
            "block_type": self.BLOCK_TYPE_TABLE,
            "table": {"property": {"row_size": row_count, "column_size": col_count}},
            "children": cell_blocks,
        }

    def _extract_text_elements(
        self,
        children: List[Dict],
        style: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """从 children 递归提取文本元素"""
        elements = []
        if style is None:
            style = {}
        style = {k: v for k, v in style.items() if v}

        for child in children:
            child_type = child.get("type")

            if child_type in ["text", "codespan"]:
                text_content = child.get("text") or child.get("raw", "")
                text_content = text_content.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

                current_style = style.copy()
                if child_type == "codespan":
                    current_style["inline_code"] = True

                limit = 2000
                if len(text_content) > limit:
                    for i in range(0, len(text_content), limit):
                        elements.append({
                            "text_run": {
                                "content": text_content[i:i + limit],
                                "text_element_style": current_style,
                            }
                        })
                else:
                    elements.append({
                        "text_run": {
                            "content": text_content,
                            "text_element_style": current_style,
                        }
                    })

            elif child_type == "strong":
                new_style = style.copy()
                new_style["bold"] = True
                elements.extend(self._extract_text_elements(child.get("children", []), new_style))

            elif child_type == "emphasis":
                new_style = style.copy()
                new_style["italic"] = True
                elements.extend(self._extract_text_elements(child.get("children", []), new_style))

            elif child_type == "strikethrough":
                new_style = style.copy()
                new_style["strikethrough"] = True
                elements.extend(self._extract_text_elements(child.get("children", []), new_style))

            elif child_type == "link":
                new_style = style.copy()
                url = child.get("attrs", {}).get("url", "")
                new_style["link"] = {"url": url}
                if not child.get("children"):
                    elements.append({
                        "text_run": {
                            "content": url,
                            "text_element_style": new_style,
                        }
                    })
                else:
                    elements.extend(self._extract_text_elements(child.get("children", []), new_style))

            elif child_type in ["math", "inline_math"]:
                math_content = child.get("attrs", {}).get("content", "") or child.get("raw", "").strip("$")
                math_content = self._sanitize_latex(math_content)
                if math_content:
                    elements.append({"equation": {"content": math_content}})

        return elements
