# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：writer.py
# @Date   ：2026/01/18 17:55
# @Author ：leemysw
# 2026/01/18 17:55   Create
# =====================================================
"""
飞书文档写入器

[INPUT]: 依赖 sdk.py 和 converters/md_to_blocks.py
[OUTPUT]: 对外提供 FeishuWriter 类，支持创建文档和写入 Markdown
[POS]: core 模块的高层写入接口
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union

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

        # 1. 预处理：提取所有本地图片并上传
        image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
        matches = image_pattern.findall(md_content)

        # 1. 转换 Markdown 为 Blocks (收集图片路径)
        blocks, image_paths = self.converter.convert(md_content)

        if not blocks:
            return []

        console.print(f"[yellow]>[/yellow] 已转换 {len(blocks)} 个 Blocks，正在写入飞书...")

        # 如果 append=False，尝试删除原有内容
        if not append:
            try:
                self.sdk.delete_blocks(document_id, document_id, 0, 500, user_access_token)
            except Exception:
                pass

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

            # 在 created_blocks 中找到所有图片 Block (类型 27)
            image_blocks = [b for b in created_blocks if b.get("block_type") == 27]

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
                        # 使用 block_id 作为 parent_node 上传
                        file_token = self.sdk.upload_image(
                            str(img_path), block_id, user_access_token
                        )

                        # 使用 batch_update 替换图片
                        requests = [
                            {
                                "replace_image": {
                                    "block_id": block_id,
                                    "token": file_token
                                }
                            }
                        ]
                        self.sdk.batch_update_blocks(
                            document_id=document_id,
                            requests=requests,
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
