# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：md_to_blocks.py
# @Date   ：2026/01/18 15:40
# @Author ：leemysw
# 2026/01/18 15:40   Create
# =====================================================
"""
Markdown → 飞书 Block 转换器

[INPUT]: 依赖 mistune 的 Markdown 解析器
[OUTPUT]: 对外提供 MarkdownToBlocks 类，将 Markdown 转换为飞书 Block 结构
[POS]: converters 模块的核心转换器
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import mistune
from mistune.plugins.table import table as table_plugin
from mistune.plugins.math import math as math_plugin


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
    BLOCK_TYPE_EQUATION = 24
    BLOCK_TYPE_QUOTE = 15
    BLOCK_TYPE_TODO = 17
    BLOCK_TYPE_DIVIDER = 22
    BLOCK_TYPE_EQUATION = 24
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
            plugins=[table_plugin, math_plugin]
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

        print(f"  [DEBUG] Mistune parsed {len(tokens)} tokens")
        blocks = []

        for token in tokens:
            block = self._convert_token(token)
            if not block:
                continue

            # Debug
            # print(f"  Block: {block}")

            # 处理列表返回 (可能返回列表)
            if isinstance(block, list):
                new_blocks = block
            else:
                new_blocks = [block]

            for b in new_blocks:
                if not isinstance(b, dict):
                    print(f"[ERROR] b is not dict: {type(b)} - {b}")
                # 过滤掉没有任何内容的文本类 Block
                bt = b.get("block_type")
                if bt in [
                    self.BLOCK_TYPE_TEXT, self.BLOCK_TYPE_HEADING1, self.BLOCK_TYPE_HEADING2,
                    self.BLOCK_TYPE_HEADING3, self.BLOCK_TYPE_HEADING4, self.BLOCK_TYPE_HEADING5,
                    self.BLOCK_TYPE_HEADING6, self.BLOCK_TYPE_HEADING7, self.BLOCK_TYPE_HEADING8,
                    self.BLOCK_TYPE_HEADING9, self.BLOCK_TYPE_BULLET, self.BLOCK_TYPE_ORDERED,
                    self.BLOCK_TYPE_QUOTE, self.BLOCK_TYPE_TODO, self.BLOCK_TYPE_EQUATION
                ]:
                    # 找到对应 payload (除 block_type 以外的第一个 key)
                    payload_key = next((k for k in b.keys() if k != "block_type"), None)
                    if payload_key and not b[payload_key].get("elements"):
                        continue
                blocks.append(b)

        # 返回 blocks 和收集到的图片路径
        return blocks, self.image_paths

    def convert_file(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        读取 Markdown 文件并转换

        Args:
            file_path: Markdown 文件路径

        Returns:
            (Blocks 列表, 图片路径列表)
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return self.convert(content)

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
            # 如果 math 出现在顶层，通常是行内公式但独占一行，或者是解析错误
            # 我们检查它是否有内容，且是否真的在顶层（这里已经是顶层循环）
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

        # 获取当前层级的文本样式 (如果段落本身有样式)
        # 飞书段落本身不支持全局样式，主要是元素样式

        for child in children:
            if child.get("type") == "image":
                # 1. 提交前面的文字
                if current_elements:
                    blocks.append({
                        "block_type": self.BLOCK_TYPE_TEXT,
                        "text": {"elements": current_elements},
                    })
                    current_elements = []

                # 2. 插入图片
                img_block = self._make_image(child)
                if img_block:
                    blocks.append(img_block)
            else:
                # 提取正常的文字元素
                elements = self._extract_text_elements([child])
                current_elements.extend(elements)

        # 3. 提交剩余文字
        if current_elements:
            blocks.append({
                "block_type": self.BLOCK_TYPE_TEXT,
                "text": {"elements": current_elements},
            })

        return blocks

    def _make_image(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理图片
        """
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
                                "text_element_style": {}
                            }
                        }
                    ]
                }
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
                for child in item.get("children", []):
                    if child.get("type") == "paragraph":
                        elements.extend(
                            self._extract_text_elements(child.get("children", []))
                        )

                blocks.append({
                    "block_type": block_type,
                    list_key: {"elements": elements},
                })

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
        """
        飞书公式编辑器不支持 \operatorname, \tag, \mathring 等，进行简单替换
        """
        if not content:
            return ""
        import re
        content = re.sub(r"\\operatorname\s*{([^}]*)}", r"\\text{\1}", content)
        content = re.sub(r"\\tag\s*{([^}]*)}", r"(\1)", content)
        content = re.sub(r"\\mathring\s*{([^}]*)}", r"\1", content)
        content = content.replace("\\mathrm", "\\text")
        return content

    def _make_equation(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        创建数学公式 Block
        根据 SDK，Block.equation 实际上是 Text 类型
        """
        content = token.get("attrs", {}).get("content", "") or token.get("raw", "").strip("$").strip()
        content = self._sanitize_latex(content)
        if not content:
            return None

        return {
            "block_type": self.BLOCK_TYPE_EQUATION,
            "equation": {
                "content": content
            },
        }

    def _make_table(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建表格 Block

        飞书 Docx 的表格比较复杂，基本结构是：
        table -> children [table_row -> children [table_cell -> children [blocks]]]
        """
        children = token.get("children", [])

        # mistune 的 table 结构通常是：
        # table -> [table_head, table_body] -> [table_row] -> [table_cell]

        all_rows_tokens = []
        for part in children:
            if part.get("type") in ["table_head", "table_body"]:
                all_rows_tokens.extend(part.get("children", []))

        col_count = 0
        cell_blocks = [] # 扁平化的所有 table_cell blocks

        for row_token in all_rows_tokens:
            cells_tokens = row_token.get("children", [])
            col_count = max(col_count, len(cells_tokens)) # 更新最大列数

            for cell_token in cells_tokens:
                # 每个单元格的内容也是一组 blocks
                cell_children_tokens = cell_token.get("children", [])
                # 将单元格内的 tokens 转换为 blocks
                current_cell_content_blocks = []
                for child_token in cell_children_tokens:
                    b = self._convert_token(child_token)
                    if not b: continue
                    if isinstance(b, list): current_cell_content_blocks.extend(b)
                    else: current_cell_content_blocks.append(b)

                # 如果单元格为空，至少加一个空的文本块
                if not current_cell_content_blocks:
                    current_cell_content_blocks.append({
                        "block_type": self.BLOCK_TYPE_TEXT,
                        "text": {"elements": []}
                    })

                cell_blocks.append({
                    "block_type": self.BLOCK_TYPE_TABLE_CELL,
                    "table_cell": {},
                    "children": current_cell_content_blocks
                })

        row_count = len(all_rows_tokens)

        # 返回 Table Block
        # 注意：cells 属性在创建时如果不知道 block_id 可以留空或者不传
        # 只要保证 children 包含正确的 table_cell 数量即可
        return {
            "block_type": self.BLOCK_TYPE_TABLE,
            "table": {
                "property": {
                    "row_size": row_count,
                    "column_size": col_count,
                },
            },
            "children": cell_blocks
        }

    def _extract_text_elements(self, children: List[Dict], style: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """从 children 递归提取文本元素"""
        elements = []
        if style is None:
            style = {}

        # 移除 style 中值为 False 或 None 的项
        style = {k: v for k, v in style.items() if v}

        for child in children:
            child_type = child.get("type")

            if child_type in ["text", "codespan"]:
                # 获取文本内容并处理换行符 (飞书 text_run 不支持换行)
                text_content = child.get("text") or child.get("raw", "")
                # 清理所有类型的换行和多余空格
                text_content = text_content.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

                current_style = style.copy()
                if child_type == "codespan":
                    current_style["inline_code"] = True

                # 处理超长内容 (飞书 text_run 限制，通常 3000-5000)
                # 我们采用 2000 作为安全阈值进行切割
                limit = 2000
                if len(text_content) > limit:
                    for i in range(0, len(text_content), limit):
                        elements.append({
                            "text_run": {
                                "content": text_content[i:i+limit],
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
                # 如果没有子元素，就用 URL 作为文本
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
                # 行内公式
                math_content = child.get("attrs", {}).get("content", "") or child.get("raw", "").strip("$")
                math_content = self._sanitize_latex(math_content)
                if math_content:
                    elements.append({
                        "equation": {
                            "content": math_content,
                        }
                    })

        return elements
