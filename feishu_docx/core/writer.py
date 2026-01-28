# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：writer.py
# @Date   ：2026/01/28 13:25
# @Author ：leemysw
# 2026/01/18 17:55   Create
# 2026/01/28 10:20   Add image refill pipeline
# 2026/01/28 12:05   Use safe console output
# 2026/01/28 12:45   Use local converter for tables
# 2026/01/28 13:10   Fill table cells after creation
# 2026/01/28 13:25   Fetch table cell blocks on demand
# =====================================================
"""
飞书文档写入器

[INPUT]: 依赖 sdk.py 和 converters/md_to_blocks.py
[OUTPUT]: 对外提供 FeishuWriter 类，支持创建文档和写入 Markdown
[POS]: core 模块的高层写入接口
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from feishu_docx.utils.console import get_console

from feishu_docx.core.converters import MarkdownToBlocks
from feishu_docx.core.sdk import FeishuSDK

console = get_console()


class FeishuWriter:
    """
    飞书文档写入器

    提供高层接口：
    - 创建文档并写入 Markdown 内容
    - 向现有文档追加内容
    - 更新文档特定 Block
    """

    def __init__(self, sdk: Optional[FeishuSDK] = None):
        """
        初始化写入器

        Args:
            sdk: FeishuSDK 实例，不传则自动创建
        """
        self.sdk = sdk or FeishuSDK()
        self.converter = MarkdownToBlocks()

    @staticmethod
    def _block_id(block: Any) -> Optional[str]:
        if isinstance(block, dict):
            return block.get("block_id")
        return getattr(block, "block_id", None)

    @staticmethod
    def _block_type(block: Any) -> Optional[int]:
        if isinstance(block, dict):
            return block.get("block_type")
        return getattr(block, "block_type", None)

    @staticmethod
    def _block_children(block: Any) -> List[str]:
        if isinstance(block, dict):
            return block.get("children") or []
        return getattr(block, "children", []) or []

    def _ordered_blocks(self, document_id: str, user_access_token: str) -> List[Any]:
        blocks = self.sdk.get_document_block_list(document_id, user_access_token)
        if not blocks:
            return []

        block_map = {
            self._block_id(b): b
            for b in blocks
            if self._block_id(b)
        }
        root_id = document_id if document_id in block_map else next(
            (self._block_id(b) for b in blocks if self._block_type(b) == 1),
            document_id,
        )

        ordered = []
        visited = set()

        def dfs(block_id: str) -> None:
            if block_id in visited:
                return
            visited.add(block_id)
            block = block_map.get(block_id)
            if not block:
                return
            ordered.append(block)
            for child_id in self._block_children(block):
                dfs(child_id)

        dfs(root_id)
        return ordered

    def _prepare_table_blocks(
        self, blocks: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        table_plans: List[Dict[str, Any]] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("block_type") != self.converter.BLOCK_TYPE_TABLE:
                continue

            cell_blocks = block.get("children") or []
            cell_contents = []
            for cell in cell_blocks:
                if isinstance(cell, dict):
                    cell_contents.append(cell.get("children") or [])
                    cell.pop("children", None)
                else:
                    cell_contents.append([])

            expected_cells = None
            table_prop = (block.get("table") or {}).get("property") or {}
            row_size = table_prop.get("row_size")
            column_size = table_prop.get("column_size")
            if isinstance(row_size, int) and isinstance(column_size, int):
                expected_cells = row_size * column_size

            if expected_cells is not None and expected_cells > len(cell_blocks):
                for _ in range(expected_cells - len(cell_blocks)):
                    cell_blocks.append(
                        {
                            "block_type": self.converter.BLOCK_TYPE_TABLE_CELL,
                            "table_cell": {},
                        }
                    )
                    cell_contents.append([])
            elif expected_cells is not None and expected_cells < len(cell_blocks):
                cell_blocks = cell_blocks[:expected_cells]
                cell_contents = cell_contents[:expected_cells]

            block.pop("children", None)
            table_plans.append(
                {
                    "cell_contents": cell_contents,
                }
            )

        return blocks, table_plans

    def _table_cell_ids(self, table_block: Any) -> List[str]:
        if isinstance(table_block, dict):
            children = table_block.get("children") or []
            if children:
                return children
            return (table_block.get("table") or {}).get("cells") or []
        return []

    def _fill_table_cells(
        self,
        document_id: str,
        created_table_block: Dict[str, Any],
        cell_contents: List[List[Dict[str, Any]]],
        user_access_token: str,
    ) -> None:
        cell_ids = self._table_cell_ids(created_table_block)
        if not cell_ids:
            table_block_id = self._block_id(created_table_block)
            if table_block_id:
                try:
                    cell_blocks = self.sdk.get_block_children(
                        document_id=document_id,
                        block_id=table_block_id,
                        user_access_token=user_access_token,
                    )
                    cell_ids = [self._block_id(b) for b in cell_blocks if self._block_id(b)]
                except Exception as e:
                    console.print(f"[yellow]![/yellow] 获取表格单元格失败: {e}")
            if not cell_ids:
                console.print("[yellow]![/yellow] 未能获取表格单元格 ID，跳过单元格内容写入")
                return

        if len(cell_ids) != len(cell_contents):
            console.print(
                f"[yellow]![/yellow] 表格单元格数量不匹配，返回 {len(cell_ids)}，期望 {len(cell_contents)}"
            )

        count = min(len(cell_ids), len(cell_contents))
        for idx in range(count):
            cell_id = cell_ids[idx]
            content_blocks = cell_contents[idx]
            if not content_blocks:
                continue
            self.sdk.create_blocks(
                document_id=document_id,
                block_id=cell_id,
                children=content_blocks,
                user_access_token=user_access_token,
            )
            time.sleep(0.35)

    def create_document(
        self,
        title: str,
        content: Optional[str] = None,
        file_path: Optional[Union[str, Path]] = None,
        folder_token: Optional[str] = None,
        user_access_token: str = "",
    ) -> Dict:
        """
        创建文档并写入 Markdown 内容

        Args:
            title: 文档标题
            content: Markdown 内容字符串（与 file_path 二选一）
            file_path: Markdown 文件路径（与 content 二选一）
            folder_token: 目标文件夹 token
            user_access_token: 用户访问凭证

        Returns:
            包含 document_id, url 的字典
        """
        # 创建空白文档
        doc = self.sdk.create_document(title, user_access_token, folder_token)
        document_id = doc["document_id"]

        # 写入内容
        if content or file_path:
            self.write_content(
                document_id=document_id,
                content=content,
                file_path=file_path,
                user_access_token=user_access_token,
            )

        return {
            "document_id": document_id,
            "url": f"https://feishu.cn/docx/{document_id}",
            "title": title,
        }

    def write_content(
        self,
        document_id: str,
        content: Optional[str] = None,
        file_path: Optional[Union[str, Path]] = None,
        user_access_token: str = "",
        append: bool = True,
        use_native_api: bool = True,
    ) -> List[Dict]:
        """
        向文档写入 Markdown 内容

        Args:
            document_id: 文档 ID
            content: Markdown 内容字符串
            file_path: Markdown 文件路径
            user_access_token: 用户访问凭证
            append: True 追加到末尾，False 清空后写入
            use_native_api: 使用飞书原生 API 转换（推荐）

        Returns:
            创建的 Block 列表
        """
        # 读取内容
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            base_dir = Path(file_path).parent
        elif content:
            md_content = content
            base_dir = Path.cwd()
        else:
            raise ValueError("必须提供 content 或 file_path")

        # 转换为 Block
        blocks: List[Dict[str, Any]] = []
        image_paths: List[str] = []

        if use_native_api:
            local_blocks, local_images = self.converter.convert(md_content)
            has_tables = any(
                isinstance(b, dict) and b.get("block_type") == self.converter.BLOCK_TYPE_TABLE
                for b in local_blocks
            )
            if local_images or has_tables:
                blocks, image_paths = local_blocks, local_images
            else:
                blocks = self.sdk.convert_markdown(md_content, user_access_token)
        else:
            blocks, image_paths = self.converter.convert(md_content)

        if not blocks:
            return []

        blocks, table_plans = self._prepare_table_blocks(blocks)

        console.print(f"[yellow]>[/yellow] 已转换 {len(blocks)} 个 Blocks，正在写入飞书...")

        if not append:
            try:
                deleted = self.sdk.clear_document(document_id, user_access_token)
                console.print(f"  - 已清空文档内容（删除约 {deleted} 个块）")
            except Exception as clear_err:
                console.print(f"[yellow]![/yellow] 清空文档失败，继续写入: {clear_err}")

        created_blocks = self.sdk.create_blocks(
            document_id=document_id,
            block_id=document_id,
            children=blocks,
            user_access_token=user_access_token,
        )

        created_table_blocks = [
            b for b in created_blocks
            if isinstance(b, dict) and b.get("block_type") == self.converter.BLOCK_TYPE_TABLE
        ]
        if len(created_table_blocks) != len(table_plans):
            console.print(
                f"[yellow]![/yellow] 表格块数量不匹配，创建 {len(created_table_blocks)}，计划 {len(table_plans)}"
            )

        resolved_table_blocks: Dict[str, Any] = {}
        if created_table_blocks:
            try:
                all_blocks = self.sdk.get_document_block_list(document_id, user_access_token)
                resolved_table_blocks = {
                    self._block_id(b): b
                    for b in all_blocks
                    if self._block_type(b) == self.converter.BLOCK_TYPE_TABLE
                }
            except Exception as e:
                console.print(f"[yellow]![/yellow] 获取表格块信息失败: {e}")

        for table_block, plan in zip(created_table_blocks, table_plans):
            cell_contents = plan.get("cell_contents") or []
            if not cell_contents:
                continue
            table_block_id = self._block_id(table_block)
            resolved_block = resolved_table_blocks.get(table_block_id) if table_block_id else None
            self._fill_table_cells(
                document_id=document_id,
                created_table_block=resolved_block or table_block,
                cell_contents=cell_contents,
                user_access_token=user_access_token,
            )

        if image_paths:
            console.print(f"> 正在为 [blue]{len(image_paths)}[/blue] 个图片 Block 回填内容...")
            console.print("  - 等待 10s 以确保 Block 一致性...")
            time.sleep(10)

            ordered_blocks = self._ordered_blocks(document_id, user_access_token)
            image_blocks = [
                b
                for b in ordered_blocks
                if self._block_type(b) == 27 and self._block_id(b) != document_id
            ]

            if len(image_blocks) != len(image_paths):
                console.print(
                    f"[yellow]![/yellow] 警告：图片 Block 数量 ({len(image_blocks)}) 与路径数量 ({len(image_paths)}) 不匹配"
                )
                count = min(len(image_blocks), len(image_paths))
            else:
                count = len(image_paths)

            for i in range(count):
                img_url = image_paths[i]
                img_block = image_blocks[i]
                block_id = self._block_id(img_block)
                if not block_id:
                    continue

                img_path = base_dir / img_url
                if img_path.exists():
                    try:
                        console.print(f"  - 上传图片: [dim]{img_url}[/dim]")
                        file_token = self.sdk.upload_image(
                            str(img_path),
                            block_id,
                            document_id,
                            user_access_token,
                        )
                        self.sdk.replace_image(
                            document_id=document_id,
                            block_id=block_id,
                            file_token=file_token,
                            user_access_token=user_access_token,
                        )
                    except Exception as e:
                        console.print(f"[red]![/red] 上传图片失败 [dim]{img_url}[/dim]: {e}")
                        try:
                            self.sdk.delete_block(document_id, block_id, user_access_token)
                            console.print(f"  - 已清理占位符 Block [dim]{block_id}[/dim]")
                        except Exception as delete_err:
                            console.print(f"  ! 清理占位符失败: {delete_err}")
                else:
                    console.print(f"[yellow]![/yellow] 找不到本地图片: [dim]{img_url}[/dim]")
                    try:
                        self.sdk.delete_block(document_id, block_id, user_access_token)
                    except Exception:
                        pass

        console.print("[green]v[/green] 文档同步完成！")
        return created_blocks

    def update_block(
        self,
        document_id: str,
        block_id: str,
        content: str,
        user_access_token: str = "",
    ) -> Dict:
        """
        更新指定 Block 的内容

        Args:
            document_id: 文档 ID
            block_id: Block ID
            content: 新的文本内容
            user_access_token: 用户访问凭证

        Returns:
            更新后的 Block
        """
        update_body = {
            "text": {
                "elements": [{"text_run": {"content": content}}]
            }
        }
        return self.sdk.update_block(
            document_id=document_id,
            block_id=block_id,
            update_body=update_body,
            user_access_token=user_access_token,
        )

    def append_markdown(
        self,
        document_id: str,
        content: str,
        user_access_token: str = "",
    ) -> List[Dict]:
        """
        追加 Markdown 内容到文档末尾

        Args:
            document_id: 文档 ID
            content: Markdown 内容
            user_access_token: 用户访问凭证

        Returns:
            创建的 Block 列表
        """
        return self.write_content(
            document_id=document_id,
            content=content,
            user_access_token=user_access_token,
            append=True,
        )
