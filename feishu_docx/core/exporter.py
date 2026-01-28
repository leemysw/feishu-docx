# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：exporter.py
# @Date   ：2026/01/28 12:05
# @Author ：leemysw
# 2025/01/09 18:30   Create
# 2026/01/28 12:05   Use safe console output
# =====================================================
"""
[INPUT]: 依赖 feishu_docx.core.parsers 的解析器，依赖 feishu_docx.auth 的认证器
[OUTPUT]: 对外提供 FeishuExporter 类，统一的导出入口
[POS]: core 模块的主导出器，是用户使用的主要接口
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import re
from pathlib import Path
from typing import Literal, Optional
from dataclasses import dataclass

from feishu_docx.utils.console import get_console

from feishu_docx.auth.oauth import OAuth2Authenticator
from feishu_docx.core.sdk import FeishuSDK
from feishu_docx.core.parsers.document import DocumentParser
from feishu_docx.core.parsers.sheet import SheetParser
from feishu_docx.core.parsers.bitable import BitableParser

console = get_console()


# ==============================================================================
# URL 解析结果
# ==============================================================================
@dataclass
class DocumentInfo:
    """文档信息"""
    doc_type: str           # "docx", "sheet", "bitable", "wiki"
    doc_id: str             # 文档 ID
    wiki_token: Optional[str] = None  # Wiki 节点 token


# ==============================================================================
# 主导出器
# ==============================================================================
class FeishuExporter:
    """
    飞书文档导出器

    支持导出以下类型的飞书云文档：
    - 云文档 (docx)
    - 电子表格 (sheet)
    - 多维表格 (bitable)
    - 知识库文档 (wiki)

    使用示例：
        # 方式一：使用 OAuth 自动授权
        exporter = FeishuExporter(
            app_id="xxx",
            app_secret="xxx"
        )
        path = exporter.export("https://xxx.feishu.cn/docx/xxx", "./output")

        # 方式二：手动传入 Token
        exporter = FeishuExporter.from_token("user_access_token_xxx")
        path = exporter.export("https://xxx.feishu.cn/docx/xxx", "./output")
    """

    # URL 模式匹配
    URL_PATTERNS = {
        # 云文档: https://xxx.feishu.cn/docx/{document_id} 或 https://xxx.larkoffice.com/docx/{document_id}
        "docx": re.compile(r"(?:feishu|larksuite)\.cn/docx/([a-zA-Z0-9]+)|larkoffice\.com/docx/([a-zA-Z0-9]+)"),
        # 电子表格: https://xxx.feishu.cn/sheets/{spreadsheet_token} 或 https://xxx.larkoffice.com/sheets/{spreadsheet_token}
        "sheet": re.compile(r"(?:feishu|larksuite)\.cn/sheets/([a-zA-Z0-9]+)|larkoffice\.com/sheets/([a-zA-Z0-9]+)"),
        # 多维表格: https://xxx.feishu.cn/base/{app_token} 或 https://xxx.larkoffice.com/base/{app_token}
        "bitable": re.compile(r"(?:feishu|larksuite)\.cn/base/([a-zA-Z0-9]+)|larkoffice\.com/base/([a-zA-Z0-9]+)"),
        # Wiki 文档: https://xxx.feishu.cn/wiki/{node_token} 或 https://xxx.larkoffice.com/wiki/{node_token}
        "wiki": re.compile(r"(?:feishu|larksuite)\.cn/wiki/([a-zA-Z0-9]+)|larkoffice\.com/wiki/([a-zA-Z0-9]+)"),
    }

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        is_lark: bool = False,
    ):
        """
        初始化导出器

        Args:
            app_id: 飞书应用 App ID（OAuth 授权需要）
            app_secret: 飞书应用 App Secret（OAuth 授权需要）
            access_token: 用户访问凭证（手动传入，与 OAuth 二选一）
            is_lark: 是否使用 Lark (海外版)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.is_lark = is_lark
        self._access_token = access_token
        self._authenticator: Optional[OAuth2Authenticator] = None
        self._sdk: Optional[FeishuSDK] = None

    @classmethod
    def from_token(cls, access_token: str) -> "FeishuExporter":
        """
        从已有 Token 创建导出器

        Args:
            access_token: 用户访问凭证

        Returns:
            FeishuExporter 实例
        """
        return cls(access_token=access_token)

    @property
    def sdk(self) -> FeishuSDK:
        """获取 SDK 实例（懒加载）"""
        if self._sdk is None:
            self._sdk = FeishuSDK()
        return self._sdk

    def get_access_token(self) -> str:
        """获取访问凭证"""
        if self._access_token:
            return self._access_token

        if not self.app_id or not self.app_secret:
            raise ValueError("需要提供 access_token 或 (app_id + app_secret)")

        if self._authenticator is None:
            self._authenticator = OAuth2Authenticator(
                app_id=self.app_id,
                app_secret=self.app_secret,
                is_lark=self.is_lark,
            )

        return self._authenticator.authenticate()

    def parse_url(self, url: str) -> DocumentInfo:
        """
        解析飞书文档 URL

        Args:
            url: 飞书文档 URL

        Returns:
            DocumentInfo 文档信息

        Raises:
            ValueError: 不支持的 URL 格式
        """
        for doc_type, pattern in self.URL_PATTERNS.items():
            match = pattern.search(url)
            if match:
                # 支持多个域名，ID 可能在 group(1) 或 group(2)
                doc_id = match.group(1) or match.group(2)
                return DocumentInfo(doc_type=doc_type, doc_id=doc_id)

        raise ValueError(f"不支持的 URL 格式: {url}")

    def export(
        self,
        url: str,
        output_dir: str | Path = ".",
        filename: Optional[str] = None,
        table_format: Literal["html", "md"] = "md",
        silent: bool = False,
        progress_callback=None,
        with_block_ids: bool = False,
    ) -> Path:
        """
        导出飞书文档为 Markdown 文件

        Args:
            url: 飞书文档 URL
            output_dir: 输出目录
            filename: 输出文件名（不含扩展名），默认使用文档标题
            table_format: 表格输出格式 ("html" 或 "md")
            silent: 是否静默模式
            progress_callback: 进度回调
            with_block_ids: 是否在导出的 Markdown 中嵌入 Block ID 注释

        Returns:
            输出文件路径
        """
        # 1. 解析 URL 和获取标题
        doc_info = self.parse_url(url)
        access_token = self.get_access_token()
        doc_title = self._get_document_title(doc_info, access_token)
        output_filename = filename or self._sanitize_filename(doc_title)

        if not silent:
            console.print(f"[blue]> 文档类型:[/blue] {doc_info.doc_type}")
            console.print(f"[blue]> 文档 ID:[/blue]  {doc_info.doc_id}")
            console.print(f"[blue]> 文档标题:[/blue] {doc_title}")

        # 2. 准备输出目录和资源目录
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 资源目录：以文件名命名的文件夹
        assets_dir = output_dir / output_filename
        assets_dir.mkdir(parents=True, exist_ok=True)

        # 3. 导出内容（核心逻辑）
        if not silent:
            console.print("[yellow]> 正在解析文档...[/yellow]")
        content = self._parse_document(
            doc_info, access_token, table_format, assets_dir,
            silent=silent, progress_callback=progress_callback,
            with_block_ids=with_block_ids
        )

        # 4. 保存到文件
        output_path = output_dir / f"{output_filename}.md"
        output_path.write_text(content, encoding="utf-8")

        console.print(f"[green]✓ 导出成功:[/green] {output_path}")

        # 如果资源目录为空，删除它
        if not any(assets_dir.iterdir()):
            assets_dir.rmdir()
        elif not silent:
            console.print(f"[green]✓ 资源目录:[/green] {assets_dir}")

        return output_path

    def export_content(
        self,
        url: str,
        table_format: Literal["html", "md"] = "html",
    ) -> str:
        """
        导出飞书文档为 Markdown 字符串（不保存到文件）

        Args:
            url: 飞书文档 URL
            table_format: 表格输出格式

        Returns:
            Markdown 格式的文档内容
        """
        doc_info = self.parse_url(url)
        access_token = self.get_access_token()
        return self._parse_document(doc_info, access_token, table_format, assets_dir=None)

    def _parse_document(
        self,
        doc_info: DocumentInfo,
        access_token: str,
        table_format: Literal["html", "md"],
        assets_dir: Optional[Path],
        silent: bool = False,
        progress_callback=None,
        with_block_ids: bool = False,
    ) -> str:
        """
        核心解析逻辑

        Args:
            doc_info: 文档信息
            access_token: 访问凭证
            table_format: 表格输出格式
            assets_dir: 资源目录（图片等），None 时使用临时目录
            silent: 是否静默模式
            progress_callback: 进度回调
            with_block_ids: 是否嵌入 Block ID 注释

        Returns:
            Markdown 内容
        """
        # 如果有资源目录，更新 SDK 的临时目录
        if assets_dir:
            self.sdk.temp_dir = assets_dir

        if doc_info.doc_type == "docx":
            parser = DocumentParser(
                document_id=doc_info.doc_id,
                user_access_token=access_token,
                table_mode=table_format,
                sdk=self.sdk,
                assets_dir=assets_dir,
                silent=silent,
                progress_callback=progress_callback,
                with_block_ids=with_block_ids,
            )
            return parser.parse()

        elif doc_info.doc_type == "sheet":
            parser = SheetParser(
                spreadsheet_token=doc_info.doc_id,
                user_access_token=access_token,
                table_mode=table_format,
                sdk=self.sdk,
                silent=silent,
                progress_callback=progress_callback,
            )
            return parser.parse()

        elif doc_info.doc_type == "bitable":
            parser = BitableParser(
                app_token=doc_info.doc_id,
                user_access_token=access_token,
                table_mode=table_format,
                sdk=self.sdk,
                silent=silent,
                progress_callback=progress_callback,
            )
            return parser.parse()

        elif doc_info.doc_type == "wiki":
            # Wiki 需要先获取实际文档信息
            node = self.sdk.get_wiki_node_metadata(doc_info.doc_id, access_token)
            obj_type = node.obj_type  # "doc", "sheet", "bitable"

            if obj_type in ("doc", "docx"):
                parser = DocumentParser(
                    document_id=node.obj_token,
                    user_access_token=access_token,
                    table_mode=table_format,
                    sdk=self.sdk,
                    assets_dir=assets_dir,
                    silent=silent,
                    progress_callback=progress_callback,
                )
                return parser.parse()
            elif obj_type == "sheet":
                parser = SheetParser(
                    spreadsheet_token=node.obj_token,
                    user_access_token=access_token,
                    table_mode=table_format,
                    sdk=self.sdk,
                    silent=silent,
                    progress_callback=progress_callback,
                )
                return parser.parse()
            elif obj_type == "bitable":
                parser = BitableParser(
                    app_token=node.obj_token,
                    user_access_token=access_token,
                    table_mode=table_format,
                    sdk=self.sdk,
                    silent=silent,
                    progress_callback=progress_callback,
                )
                return parser.parse()
            else:
                raise ValueError(f"不支持的 Wiki 节点类型: {obj_type}")

        else:
            raise ValueError(f"不支持的文档类型: {doc_info.doc_type}")

    def _get_document_title(self, doc_info: DocumentInfo, access_token: str) -> str:
        """获取文档标题"""
        try:
            if doc_info.doc_type == "docx":
                info = self.sdk.get_document_info(doc_info.doc_id, access_token)
                return info.get("title", doc_info.doc_id)
            elif doc_info.doc_type == "sheet":
                info = self.sdk.get_spreadsheet_info(doc_info.doc_id, access_token)
                return info.get("title", doc_info.doc_id)
            elif doc_info.doc_type == "bitable":
                info = self.sdk.get_bitable_info(doc_info.doc_id, access_token)
                return info.get("title", doc_info.doc_id)
            elif doc_info.doc_type == "wiki":
                node = self.sdk.get_wiki_node_metadata(doc_info.doc_id, access_token)
                return node.title or doc_info.doc_id
        except Exception: # noqa
            pass
        return doc_info.doc_id

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """清理文件名，移除非法字符"""
        import re
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = name.strip('. ')
        return name or "untitled"
