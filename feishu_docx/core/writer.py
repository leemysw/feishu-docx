# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：writer.py
# @Date   ：2026/01/27 13:40
# @Author ：leemysw
# 2026/01/18 17:55   Create
# 2026/01/27 13:40   Improve image refill pipeline
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

from rich.console import Console

from feishu_docx.core.converters import MarkdownToBlocks
from feishu_docx.core.sdk import FeishuSDK

console = Console()


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
    def _build_block_map(blocks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return {b.get("block_id"): b for b in blocks if b.get("block_id")}

    def _ordered_blocks(self, document_id: str, user_access_token: str) -> List[Dict[str, Any]]:
        blocks = self.sdk.get_document_block_list(document_id, user_access_token)
        if not blocks:
            return []

        block_map = self._build_block_map(blocks)
        root_id = document_id if document_id in block_map else next(
            (b.get("block_id") for b in blocks if b.get("block_type") == 1),
            document_id,
        )

        ordered: List[Dict[str, Any]] = []
        visited = set()

        def dfs(block_id: str) -> None:
            if block_id in visited:
                return
            visited.add(block_id)
            block = block_map.get(block_id)
            if not block:
                return
            ordered.append(block)
            for child_id in block.get("children") or []:
                dfs(child_id)

        dfs(root_id)
        return ordered

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

        # 1. 转换 Markdown 为 Blocks (收集图片路径)
        blocks, image_paths = self.converter.convert(md_content)

        if not blocks:
            return []

        console.print(f"[yellow]>[/yellow] 已转换 {len(blocks)} 个 Blocks，正在写入飞书...")

        # 如果 append=False，尝试删除原有内容
        if not append:
            try:
                deleted = self.sdk.clear_document(document_id, user_access_token)
                console.print(f"  - 已清空文档内容（删除约 {deleted} 个块）")
            except Exception as clear_err:
                console.print(f"[yellow]![/yellow] 清空文档失败，继续写入: {clear_err}")

        # 2. 写入初始内容 (包含图片占位符)
        created_blocks = self.sdk.create_blocks(
            document_id=document_id,
            block_id=document_id,
            children=blocks,
            user_access_token=user_access_token,
        )

        # 3. 回填图片
        if image_paths:
            console.print(f"> 正在为 [blue]{len(image_paths)}[/blue] 个图片 Block 回填内容...")
            console.print("  - 等待 10s 以确保 Block 一致性...")
            time.sleep(10)

            ordered_blocks = self._ordered_blocks(document_id, user_access_token)
            image_blocks = [
                b
                for b in ordered_blocks
                if b.get("block_type") == 27 and b.get("block_id") != document_id
            ]

            if len(image_blocks) != len(image_paths):
                console.print(f"[yellow]![/yellow] 警告：图片 Block 数量 ({len(image_blocks)}) 与路径数量 ({len(image_paths)}) 不匹配")
                # 尽量匹配，取最小值
                count = min(len(image_blocks), len(image_paths))
            else:
                count = len(image_paths)

            for i in range(count):
                img_url = image_paths[i]
                img_block = image_blocks[i]
                block_id = img_block.get("block_id")

                # 获取图片的绝对路径
                img_path = base_dir / img_url
                if img_path.exists():
                    try:
                        console.print(f"  - 上传图片: [dim]{img_url}[/dim]")
                        # 使用 document_id 作为 parent_node 上传
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
                        # 失败后删除占位符，保持文档整洁
                        try:
                            self.sdk.delete_block(document_id, block_id, user_access_token)
                            console.print(f"  - 已清理占位符 Block [dim]{block_id}[/dim]")
                        except Exception as delete_err:
                            console.print(f"  ! 清理占位符失败: {delete_err}")
                else:
                    console.print(f"[yellow]![/yellow] 找不到本地图片: [dim]{img_url}[/dim]")
                    # 删除占位符
                    try:
                        self.sdk.delete_block(document_id, block_id, user_access_token)
                    except:
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
