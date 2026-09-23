# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：document.py
# @Date   ：2026/01/28 16:00
# @Author ：leemysw
# 2025/01/09 18:30   Create
# 2026/01/28 12:05   Use safe console output
# 2026/01/28 16:00   Add whiteboard metadata export support
# =====================================================
"""
[INPUT]: 依赖 feishu_docx.core.sdk 的 FeishuSDK, 依赖 feishu_docx.schema 的数据模型
[OUTPUT]: 对外提供 DocumentParser 类，将飞书云文档解析为 Markdown
[POS]: parsers 模块的文档解析器，处理 docx 类型文档
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

from lark_oapi.api.docx.v1 import Block
from feishu_docx.utils.console import get_console

from feishu_docx.core.sdk import FeishuSDK
from feishu_docx.schema.code_style import CODE_STYLE_MAP
from feishu_docx.schema.models import BlockType, SheetValueMode, TableMode
from feishu_docx.utils.progress import ProgressManager
from feishu_docx.utils.render_table import render_table_html, render_table_markdown

console = get_console()


class DocumentParser:
    """
    飞书云文档解析器

    将飞书 docx 文档解析为 Markdown 格式。

    使用示例：
        parser = DocumentParser(
            document_id="xxxx",
            user_access_token="xxxx"
        )
        markdown_content = parser.parse()
    """

    def __init__(
            self,
            document_id: str,
            user_access_token: str,
            table_mode: str = "md",
            sheet_value_mode: str = "display",
            sdk: Optional[FeishuSDK] = None,
            assets_dir: Optional[Path] = None,
            silent: bool = False,
            progress_callback=None,
            with_block_ids: bool = False,
            export_board_metadata: bool = False,
    ):
        """
        初始化文档解析器

        Args:
            document_id: 文档 ID
            user_access_token: 用户访问凭证
            table_mode: 表格输出格式 ("html" 或 "md")
            sheet_value_mode: 嵌入电子表格的单元格值导出模式 ("display" 或 "formula")
            sdk: 可选的 SDK 实例（用于共享临时目录）
            assets_dir: 资源文件保存目录（图片等）
            silent: 是否静默模式（不输出 Rich 进度）
            progress_callback: 进度回调函数 (stage: str, current: int, total: int)
            with_block_ids: 是否在导出的 Markdown 中嵌入 Block ID 注释
            export_board_metadata: 是否导出画板节点元数据
        """
        self.sdk = sdk or FeishuSDK()
        self.table_mode = TableMode(table_mode)
        self.sheet_value_mode = SheetValueMode(sheet_value_mode)
        self.user_access_token = user_access_token
        self.document_id = document_id
        self.assets_dir = assets_dir

        # 进度管理器
        self.pm = ProgressManager(silent=silent, callback=progress_callback)

        # Block ID 嵌入选项
        self.with_block_ids = with_block_ids

        # 画板元数据导出选项
        self.export_board_metadata = export_board_metadata

        # Block 缓存
        self.blocks_map: Dict[str, Block] = {}
        self.root_block: Optional[Block] = None
        self.synced_subtree_cache: Dict[Tuple[str, str], Tuple[Block, Dict[str, Block]]] = {}
        self.link_title_cache: Dict[str, Optional[str]] = {}

        # order 序列号
        self.last_order_seq = 1

        # 预处理
        self._preprocess()

    def _preprocess(self):
        """预处理：获取 Block 列表并构建树结构"""
        pm = self.pm

        # 阶段1: 获取 Block 列表
        with pm.spinner("获取文档结构..."):
            raw_data = self.sdk.docx.get_block_list(
                document_id=self.document_id,
                access_token=self.user_access_token,
            )

        total_blocks = len(raw_data)
        pm.log(f"  [dim]发现 {total_blocks} 个 Block[/dim]")
        pm.report(f"发现  {total_blocks} 个 Block", total_blocks, total_blocks)

        if total_blocks == 0:
            return

        # 阶段2: 反序列化 Block
        with pm.bar("解析 Block...", total_blocks) as advance:
            for item in raw_data:
                self.blocks_map[item.block_id] = item
                advance()  # noqa

        # 确定根节点
        self.root_block = next(
            (b for b in self.blocks_map.values() if b.block_type == BlockType.PAGE),
            None,
        )
        if not self.root_block and raw_data:
            first_id = raw_data[0].block_id
            self.root_block = self.blocks_map.get(first_id)

        pm.log("  [dim]预处理完成[/dim]")
        pm.report("预处理完成", total_blocks, total_blocks)

    def parse(self) -> str:
        """
        解析文档为 Markdown

        Returns:
            Markdown 格式的文档内容
        """
        pm = self.pm

        if not self.root_block:
            pm.log("[yellow]> 未找到根 Block，无法解析文档[/yellow]")
            return ""

        total_blocks = len(self.blocks_map)

        # 阶段4: 渲染 Markdown
        with pm.bar("渲染 Markdown...", total_blocks) as advance:
            title = self._render_text_payload(self.root_block.page)
            body = self._recursive_render(self.root_block, advance=advance)

        pm.log(f"  [dim]渲染完成 ({total_blocks} blocks)[/dim]")
        pm.report("渲染完成", total_blocks, total_blocks)

        return f"# {title}\n{body}"

    def _get_sub_blocks(self, block: Block, block_lookup: Optional[Dict[str, Block]] = None) -> List[Block]:
        """获取 block 的子 Block 列表"""
        lookup = block_lookup or self.blocks_map
        if not block.children:
            return []
        sub_blocks = [lookup[sub_id] for sub_id in block.children]
        return sub_blocks

    def _get_synced_subtree(self, source_document_id: str, source_block_id: str) -> Optional[Tuple[Block, Dict[str, Block]]]:
        cache_key = (source_document_id, source_block_id)
        if cache_key in self.synced_subtree_cache:
            return self.synced_subtree_cache[cache_key]

        subtree = self.sdk.docx.get_block_subtree(
            document_id=source_document_id,
            block_id=source_block_id,
            access_token=self.user_access_token,
        )
        if not subtree:
            return None

        subtree_map = {block.block_id: block for block in subtree}
        if source_block_id not in subtree_map:
            raise RuntimeError(f"同步块子树缺少根 Block: {source_document_id}/{source_block_id}")
        root_block = subtree_map[source_block_id]
        self.synced_subtree_cache[cache_key] = (root_block, subtree_map)
        return root_block, subtree_map

    def _resolve_reference_synced_children(
            self,
            block: Block,
    ) -> List[Tuple[Block, Dict[str, Block]]]:
        if not block.reference_synced:
            return []

        source_document_id = block.reference_synced.source_document_id
        source_block_id = block.reference_synced.source_block_id
        if not source_document_id or not source_block_id:
            return []

        if source_document_id == self.document_id and source_block_id in self.blocks_map:
            source_block = self.blocks_map[source_block_id]
            return [(child, self.blocks_map) for child in self._get_sub_blocks(source_block, self.blocks_map)]

        subtree = self._get_synced_subtree(source_document_id, source_block_id)
        if not subtree:
            return []

        source_block, subtree_map = subtree
        return [(child, subtree_map) for child in self._get_sub_blocks(source_block, subtree_map)]

    def _recursive_render(
            self,
            block: Block,
            depth: int = 0,
            advance: Optional[Callable[[], None]] = None,
            block_lookup: Optional[Dict[str, Block]] = None,
    ) -> str:
        """递归渲染 Block 树"""
        content = ""
        lookup = block_lookup or self.blocks_map

        # 更新进度
        if advance:
            advance()

        # 1. 渲染自身内容
        self_content = self._render_block_self(block)

        # 2. 特殊容器处理
        if block.block_type == BlockType.TABLE:
            return self._render_table(block, lookup)

        # 3. 递归渲染子节点
        children_content = []
        if block.block_type == BlockType.REFERENCE_SYNCED:
            child_entries = self._resolve_reference_synced_children(block)
        else:
            child_entries = [(child, lookup) for child in self._get_sub_blocks(block, lookup)]

        for child, child_lookup in child_entries:
            child_text = self._recursive_render(child, depth + 1, advance, child_lookup)
            if child_text:
                children_content.append(child_text)

        joined_children = "\n\n".join(children_content) if children_content else ""

        # 4. 组合逻辑
        if self_content:
            content += self_content

        if joined_children:
            bt = block.block_type

            # 引用容器 & Callout：给子内容加前缀
            if bt in [BlockType.QUOTE, BlockType.QUOTE_CONTAINER, BlockType.CALLOUT]:
                prefixed = "\n".join([f"> {line}" for line in joined_children.split("\n")])
                content += f"\n{prefixed}"

            # 列表：子内容缩进
            elif bt in [BlockType.BULLET, BlockType.ORDERED, BlockType.TODO]:
                indented = "\n".join([f"    {line}" for line in joined_children.split("\n")])
                content += f"\n{indented}"

            # 其他：直接追加
            else:
                content += f"\n\n{joined_children}"

        return content.strip()

    def _render_block_self(self, block: Block) -> str:
        """根据 block_type 渲染对应的 Markdown"""
        content = self._render_block_content(block)

        # 嵌入 Block ID 注释
        if self.with_block_ids and content:
            return f"<!-- block:{block.block_id} -->\n{content}\n<!-- /block -->"
        return content

    def _render_block_content(self, block: Block) -> str:
        """渲染 Block 的实际内容"""
        bt = block.block_type

        # 文本类
        if bt == BlockType.TEXT:
            return self._render_text_payload(block.text)

        # 标题类 (3-11)
        if BlockType.HEADING1 <= bt <= BlockType.HEADING9:
            level = bt - 2
            payload = getattr(block, f"heading{level}", None)
            return f"{'#' * level} {self._render_text_payload(payload)}"

        # 列表类
        if bt == BlockType.BULLET:
            return f"- {self._render_text_payload(block.bullet)}"

        if bt == BlockType.ORDERED:
            seq = "1"
            if block.ordered and block.ordered.style:
                seq = block.ordered.style.sequence or "1"
                if seq == "auto":
                    seq = self.last_order_seq + 1
                    self.last_order_seq = seq
                else:
                    self.last_order_seq = int(seq)
            return f"{seq}. {self._render_text_payload(block.ordered)}"

        if bt == BlockType.TODO:
            status = "[x]" if block.todo and block.todo.style and block.todo.style.done else "[ ]"
            return f"- {status} {self._render_text_payload(block.todo)}"

        # 功能类
        if bt == BlockType.CODE:
            lang = "text"
            if block.code and block.code.style and block.code.style.language:
                lang = CODE_STYLE_MAP.get(block.code.style.language, "text")
            return f"```{lang}\n{self._render_text_payload(block.code)}\n```"

        if bt == BlockType.QUOTE:
            return f"> {self._render_text_payload(block.quote)}"

        if bt == BlockType.CALLOUT:
            return f"> 💡 {self._render_text_payload(block.callout)}" # noqa

        if bt == BlockType.DIVIDER:
            return "---"

        if bt == BlockType.IMAGE:
            if not block.image or not block.image.token:
                return ""
            file_path_or_url = self.sdk.media.get_image(block.image.token, access_token=self.user_access_token)
            if file_path_or_url:
                if file_path_or_url.startswith(("http://", "https://")):
                    return f"![image]({file_path_or_url})"
                # 使用相对路径：资源目录名/文件名
                if self.assets_dir:
                    rel_path = f"{self.assets_dir.name}/{Path(file_path_or_url).name}"
                    return f"![image]({rel_path})"
                return f"![image]({file_path_or_url})"
            else:
                # 降级方案：使用临时下载 URL（适用于只读权限）
                download_url = self.sdk.media.get_file_download_url(block.image.token, self.user_access_token)
                if download_url:
                    return f"![image]({download_url})"
                return f"![图片下载失败（无权限）]({block.image.token})"

        if bt == BlockType.BOARD:
            if not block.board or not block.board.token:
                return ""

            whiteboard_id = block.board.token

            # 根据配置决定是否导出元数据
            if self.export_board_metadata:
                # 同时导出图片和元数据
                board_data = self.sdk.media.get_whiteboard_with_metadata(
                    whiteboard_id=whiteboard_id,
                    access_token=self.user_access_token,
                    export_image=True,
                    export_metadata=True,
                )
                if not board_data:
                    # 降级：无法导出时返回友好提示
                    return f"<!-- 画板 {whiteboard_id} 需要相应权限才能导出 -->"

                # 生成 Markdown
                content_parts = []

                # 图片部分
                if "image_path" in board_data:
                    file_path = board_data["image_path"]
                    if self.assets_dir:
                        rel_path = f"{self.assets_dir.name}/{Path(file_path).name}"
                        content_parts.append(f"![whiteboard]({rel_path})")
                    else:
                        content_parts.append(f"![whiteboard]({file_path})")

                # 元数据部分
                if "nodes" in board_data:
                    metadata_md = self._render_board_metadata(board_data["nodes"])
                    if metadata_md:
                        content_parts.append(metadata_md)

                return "\n\n".join(content_parts)
            else:
                # 仅导出图片（现有逻辑）
                file_path = self.sdk.media.get_whiteboard(whiteboard_id, access_token=self.user_access_token)
                if file_path:
                    # 使用相对路径
                    if self.assets_dir:
                        rel_path = f"{self.assets_dir.name}/{Path(file_path).name}"
                        return f"![whiteboard]({rel_path})"
                    return f"![whiteboard]({file_path})"
                # 降级：无法下载时返回占位符（画板没有临时URL方案）
                return f"<!-- 画板 {whiteboard_id} 需要相应权限才能下载 -->"

        # 电子表格
        if bt == BlockType.SHEET:
            if not block.sheet:
                return ""
            token_parts = block.sheet.token.split("_")
            if len(token_parts) >= 2:
                return self.sdk.sheet.get_sheet(
                    sheet_token=token_parts[0],
                    sheet_id=token_parts[1],
                    access_token=self.user_access_token,
                    table_mode=self.table_mode,
                    value_mode=self.sheet_value_mode,
                ) or ""
            return ""

        # 多维表格
        if bt == BlockType.BITABLE:
            if not block.bitable:
                return ""
            token_parts = block.bitable.token.split("_")
            if len(token_parts) >= 2:
                return self.sdk.bitable.get_bitable(
                    app_token=token_parts[0],
                    table_id=token_parts[1],
                    access_token=self.user_access_token,
                    table_mode=self.table_mode,
                ) or ""
            return ""

        # 引用 Block
        if bt == BlockType.REFERENCE_BLOCK:
            if not block.reference_base:
                return ""
            token_parts = block.reference_base.token.split("_")
            if len(token_parts) == 2 and token_parts[1].startswith("tb"):
                return self.sdk.bitable.get_bitable(
                    app_token=token_parts[0],
                    table_id=token_parts[1],
                    view_id=block.reference_base.view_id,
                    access_token=self.user_access_token,
                    table_mode=self.table_mode,
                ) or ""
            return ""

        # 文档小组件 Block
        if bt == BlockType.ADD_ONS:
            if not block.add_ons or not block.add_ons.record:
                return ""
            try:
                record = json.loads(block.add_ons.record)
            except (json.JSONDecodeError, TypeError):
                return ""
            widget_data = record.get("data")
            if not widget_data:
                return ""
            view = record.get("view", "")
            if view in ("codeChart", "flowChart"):
                lang = "mermaid"
            elif view == "uml":
                lang = "plantuml"
            else:
                lang = "text"
            return f"```{lang}\n{widget_data}\n```"

        # 文件/附件 Block
        if bt == BlockType.FILE:
            if not block.file:
                return ""
            file_name = block.file.name or "未命名文件"
            file_token = block.file.token
            if self.assets_dir:
                file_path_or_url = self.sdk.media.get_file(
                    file_token=file_token,
                    access_token=self.user_access_token,
                    file_name=file_name,
                )
                if file_path_or_url:
                    if file_path_or_url.startswith(("http://", "https://")):
                        return f"📎 [{file_name}]({file_path_or_url})"
                    rel_path = f"{self.assets_dir.name}/{Path(file_path_or_url).name}"
                    return f"📎 [{file_name}]({rel_path})"

            download_url = self.sdk.media.get_file_download_url(file_token, self.user_access_token)
            if download_url:
                return f"📎 [{file_name}]({download_url})"
            # 回退：使用 token 作为标识
            return f"📎 {file_name} (token: `{file_token}`)"

        if bt == BlockType.LINK_PREVIEW:
            if not block.link_preview:
                return ""
            return self._render_reference_link(block.link_preview.url, block_title=None, as_block=True)

        return ""

    def _render_text_payload(self, payload) -> str:
        """渲染文本类 Payload"""
        if not payload or not hasattr(payload, "elements"):
            return ""

        result = []
        for el in payload.elements:
            text = ""
            if el.text_run:
                text = el.text_run.content
                style = el.text_run.text_element_style
                if style:
                    if style.inline_code:
                        text = f"`{text}`"
                    if style.bold:
                        text = f"**{text}**" if text else ""
                    if style.italic:
                        text = f"*{text}*"
                    if style.strikethrough:
                        text = f"~~{text}~~"
                    if style.underline:
                        text = f"<u>{text}</u>"
                    if style.link:
                        text = f"[{text}]({self._normalize_link_url(style.link.url)})"
                    if style.bold and text:
                        text += " "
            elif el.mention_user:
                user_name = self.sdk.contact.get_user_name(el.mention_user.user_id, self.user_access_token)
                text = f"@{user_name}"
            elif el.mention_doc:
                title = el.mention_doc.title or el.mention_doc.token
                text = self._render_reference_link(el.mention_doc.url, block_title=title)
            elif el.equation:
                text = f"${el.equation.content}$"
            elif el.link_preview:
                text = self._render_reference_link(el.link_preview.url, block_title=el.link_preview.title)

            result.append(text)
        return "".join(result)

    @staticmethod
    def _normalize_link_url(url: str | None) -> str:
        raw_url = (url or "").strip()
        if not raw_url:
            return ""

        parsed = urlparse(raw_url)
        if parsed.scheme or parsed.netloc:
            return raw_url

        decoded_url = unquote(raw_url)
        decoded = urlparse(decoded_url)
        if decoded.scheme or decoded.netloc:
            return decoded_url
        return raw_url

    @staticmethod
    def _is_feishu_doc_url(url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return any(domain in host for domain in ("feishu.cn", "larksuite.cn", "larkoffice.com"))

    def _resolve_link_title(self, url: str) -> Optional[str]:
        if url in self.link_title_cache:
            return self.link_title_cache[url]

        if not self._is_feishu_doc_url(url):
            self.link_title_cache[url] = None
            return None

        try:
            parsed = urlparse(url)
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) < 2:
                self.link_title_cache[url] = None
                return None

            kind, token = parts[-2], parts[-1]
            title: Optional[str] = None

            if kind in ("doc", "docx"):
                info = self.sdk.docx.get_document_info(token, self.user_access_token)
                title = info.get("title")
            elif kind in ("sheet", "sheets"):
                info = self.sdk.sheet.get_spreadsheet_info(token, self.user_access_token)
                title = info.get("title")
            elif kind == "base":
                info = self.sdk.bitable.get_bitable_info(token, self.user_access_token)
                title = info.get("title")
            elif kind == "wiki":
                node = self.sdk.wiki.get_node_metadata(token, self.user_access_token)
                title = getattr(node, "title", None)

            self.link_title_cache[url] = title
            return title
        except Exception:
            self.link_title_cache[url] = None
            return None

    def _render_reference_link(
            self,
            url: Optional[str],
            block_title: Optional[str] = None,
            *,
            as_block: bool = False,
    ) -> str:
        title = (block_title or "").strip()
        link_url = self._normalize_link_url(url)

        if link_url:
            resolved_title = title or self._resolve_link_title(link_url) or link_url
            rendered = f"[{resolved_title}]({link_url})"
        else:
            rendered = title

        if as_block and rendered:
            return f"> Link: {rendered}"
        return rendered

    def _render_table(self, table_block: Block, block_lookup: Optional[Dict[str, Block]] = None) -> str:
        """渲染表格 Block"""
        lookup = block_lookup or self.blocks_map
        if not table_block.table or not table_block.table.property:
            return "[空表格]"

        props = table_block.table.property
        row_count = props.row_size
        col_count = props.column_size
        merge_infos = props.merge_info

        # 获取所有 Cell Block
        sub_blocks = self._get_sub_blocks(table_block, lookup)
        all_cell_blocks = sub_blocks if sub_blocks else []
        global_cell_cursor = 0

        # 构建网格
        visited = [[False for _ in range(col_count)] for _ in range(row_count)]
        grid_data: List[List[Optional[Tuple[str, int, int]]]] = [
            [None for _ in range(col_count)] for _ in range(row_count)
        ]

        for r_idx in range(row_count):
            for c_idx in range(col_count):
                if visited[r_idx][c_idx]:
                    continue

                flat_index = r_idx * col_count + c_idx
                if flat_index < len(merge_infos):
                    m_info = merge_infos[flat_index]
                    r_span = m_info.row_span
                    c_span = m_info.col_span
                else:
                    r_span, c_span = 1, 1

                # 标记覆盖区域
                for rs in range(r_span):
                    for cs in range(c_span):
                        if r_idx + rs < row_count and c_idx + cs < col_count:
                            visited[r_idx + rs][c_idx + cs] = True

                # 获取内容
                cell_content = ""
                if global_cell_cursor < len(all_cell_blocks):
                    cell_block = all_cell_blocks[global_cell_cursor]
                    cell_sub_blocks = self._get_sub_blocks(cell_block, lookup)
                    inner_texts = [self._recursive_render(child, depth=0, block_lookup=lookup) for child in cell_sub_blocks]
                    cell_content = "<br>".join(inner_texts)
                    global_cell_cursor += 1

                grid_data[r_idx][c_idx] = (cell_content, r_span, c_span)

        # 渲染输出
        if self.table_mode == TableMode.HTML:
            return render_table_html(grid_data, row_count, col_count)
        else:
            return render_table_markdown(grid_data, row_count, col_count)

    def _render_board_metadata(self, nodes: List[dict]) -> str:
        """
        渲染画板节点元数据为 Markdown

        Args:
            nodes: 节点列表

        Returns:
            Markdown 格式的元数据描述
        """
        if not nodes:
            return ""

        lines = [
            "<details>",
            "<summary>📊 画板结构信息</summary>",
            "",
            f"**节点数量**: {len(nodes)}",
            "",
            "| 节点ID | 类型 | 位置 | 大小 | 文本内容 |",
            "|--------|------|------|------|----------|",
        ]

        # 限制显示前20个节点，避免输出过长
        for node in nodes[:20]:
            node_id = node.get("node_id", "N/A")
            # 截取前8位节点ID
            if len(node_id) > 8:
                node_id = f"{node_id[:8]}..."

            node_type = node.get("type", "unknown")
            pos = node.get("position", {})
            size = node.get("size", {})

            pos_str = f"({pos.get('x', 0)}, {pos.get('y', 0)})" if pos else "N/A"
            size_str = f"{size.get('width', 0)}×{size.get('height', 0)}" if size else "N/A"

            # 提取文本内容，限制长度
            text = node.get("text", "")
            if text:
                # 限制文本长度为30个字符，超过则截断
                if len(text) > 30:
                    text = text[:27] + "..."
            else:
                text = "-"

            lines.append(f"| {node_id} | {node_type} | {pos_str} | {size_str} | {text} |")

        if len(nodes) > 20:
            lines.append(f"| ... | 共 {len(nodes)} 个节点 | ... | ... | ... |")

        lines.extend(["", "</details>"])

        return "\n".join(lines)
