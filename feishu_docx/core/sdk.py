# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：sdk.py
# @Date   ：2026/01/28 13:20
# @Author ：leemysw
# 2025/01/09 18:30   Create
# 2026/01/28 10:20   Add image upload helpers and chunked create
# 2026/01/28 12:05   Use safe console output
# 2026/01/28 13:20   Add block children fetch helper
# =====================================================
"""
[INPUT]: 依赖 lark_oapi 的飞书 SDK，依赖 feishu_docx.schema.models 的数据模型
[OUTPUT]: 对外提供 FeishuSDK 类，封装所有飞书 API 调用
[POS]: core 模块的 API 封装层，被 parsers 调用
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import (
    AppTable,
    AppTableFieldForList,
    ListAppTableFieldRequest,
    ListAppTableFieldResponse,
    ListAppTableRequest,
    ListAppTableResponse,
    SearchAppTableRecordRequest,
    SearchAppTableRecordRequestBody,
    SearchAppTableRecordResponse,
)
from lark_oapi.api.bitable.v1 import GetAppRequest, GetAppResponse
from lark_oapi.api.board.v1 import (
    DownloadAsImageWhiteboardRequest,
    DownloadAsImageWhiteboardResponse,
)
from lark_oapi.api.contact.v3 import GetUserRequest, GetUserResponse
from lark_oapi.api.docx.v1 import Block, ListDocumentBlockRequest, ListDocumentBlockResponse
from lark_oapi.api.drive.v1 import DownloadMediaRequest, DownloadMediaResponse
from lark_oapi.api.sheets.v3 import QuerySpreadsheetSheetRequest, QuerySpreadsheetSheetResponse, Sheet
from lark_oapi.api.wiki.v2 import GetNodeSpaceRequest, GetNodeSpaceResponse, Node
from lark_oapi.core import BaseResponse
from feishu_docx.utils.console import get_console

from feishu_docx.schema.models import TableMode
from feishu_docx.utils.render_table import convert_to_html, convert_to_markdown

console = get_console()


class FeishuSDK:
    """
    飞书 API 封装

    提供统一的接口调用飞书开放平台 API，包括：
    - 文档 Block 列表
    - 电子表格数据
    - 多维表格数据
    - 图片/附件下载
    - 画板导出
    """

    def __init__(self, temp_dir: Optional[Path] = None):
        """
        初始化 SDK

        Args:
            temp_dir: 临时文件存储目录，默认使用系统临时目录
        """
        # 创建 lark client，启用手动设置 token
        self.client = (
            lark.Client.builder()
            .enable_set_token(True)
            .log_level(lark.LogLevel.ERROR)
            .build()
        )
        # 临时文件目录
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "feishu_docx"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    # ==========================================================================
    # 用户信息
    # ==========================================================================
    def get_user_name(self, user_id: str, user_access_token: str) -> str:
        """
        获取用户名称

        Args:
            user_id: 用户 ID (open_id)
            user_access_token: 用户访问凭证

        Returns:
            用户名称，失败时返回原 user_id
        """
        request = (
            GetUserRequest.builder()
            .user_id(user_id)
            .user_id_type("open_id")
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: GetUserResponse = self.client.contact.v3.user.get(request, option)

        if not response.success():
            self._log_error("contact.v3.user.get", response)
            return user_id

        return response.data.user.name

    # ==========================================================================
    # Wiki 知识库
    # ==========================================================================
    def get_wiki_node_metadata(self, node_token: str, user_access_token: str) -> Optional[Node]:
        """
        获取知识库节点元数据

        Args:
            node_token: 节点 token
            user_access_token: 用户访问凭证

        Returns:
            节点信息
        """
        request = (
            GetNodeSpaceRequest.builder()
            .token(node_token)
            .obj_type("wiki")
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: GetNodeSpaceResponse = self.client.wiki.v2.space.get_node(request, option)

        if not response.success():
            self._log_error("wiki.v2.space.get_node", response)
            raise RuntimeError("获取知识库节点失败")

        return response.data.node

    # ==========================================================================
    # 云文档
    # ==========================================================================
    def get_document_info(self, document_id: str, user_access_token: str) -> dict:
        """
        获取云文档基本信息（包含标题）

        Args:
            document_id: 文档 ID
            user_access_token: 用户访问凭证

        Returns:
            包含 document_id, revision_id, title 的字典
        """
        from lark_oapi.api.docx.v1 import GetDocumentRequest, GetDocumentResponse

        request = GetDocumentRequest.builder().document_id(document_id).build()
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: GetDocumentResponse = self.client.docx.v1.document.get(request, option)

        if not response.success():
            self._log_error("docx.v1.document.get", response)
            return {"document_id": document_id, "title": document_id}

        doc = response.data.document
        return {
            "document_id": doc.document_id,
            "revision_id": doc.revision_id,
            "title": doc.title or document_id,
        }

    def get_document_block_list(self, document_id: str, user_access_token: str) -> List[Block]:
        """
        获取文档所有 Block

        Args:
            document_id: 文档 ID
            user_access_token: 用户访问凭证

        Returns:
            Block 列表（原始 dict）
        """
        has_more = True
        page_token = None
        blocks = []

        while has_more:
            request = (
                ListDocumentBlockRequest.builder()
                .document_id(document_id)
                .page_size(500)
                .document_revision_id(-1)
                .build()
            )
            if page_token:
                request.add_query("page_token", page_token)

            option = lark.RequestOption.builder().user_access_token(user_access_token).build()
            response: ListDocumentBlockResponse = self.client.docx.v1.document_block.list(request, option)

            if not response.success():
                self._log_error("docx.v1.document_block.list", response)
                raise RuntimeError("获取文档 Block 列表失败")

            has_more = response.data.has_more
            page_token = response.data.page_token
            blocks.extend(response.data.items)

        return blocks

    def get_block_children(self, document_id: str, block_id: str, user_access_token: str) -> List[Block]:
        """
        获取指定 Block 的子 Block

        Args:
            document_id: 文档 ID
            block_id: 父 Block ID
            user_access_token: 用户访问凭证

        Returns:
            子 Block 列表（原始 dict）
        """
        from lark_oapi.api.docx.v1 import (
            GetDocumentBlockChildrenRequest,
            GetDocumentBlockChildrenResponse,
        )

        has_more = True
        page_token = None
        blocks: List[Block] = []

        while has_more:
            request = (
                GetDocumentBlockChildrenRequest.builder()
                .document_id(document_id)
                .block_id(block_id)
                .document_revision_id(-1)
                .page_size(500)
                .with_descendants(False)
                .build()
            )
            if page_token:
                request.add_query("page_token", page_token)

            option = lark.RequestOption.builder().user_access_token(user_access_token).build()
            response: GetDocumentBlockChildrenResponse = (
                self.client.docx.v1.document_block_children.get(request, option)
            )

            if not response.success():
                self._log_error("docx.v1.document_block_children.get", response)
                raise RuntimeError("获取 Block 子列表失败")

            has_more = response.data.has_more
            page_token = response.data.page_token
            blocks.extend(response.data.items)

        return blocks

    def create_document(
            self, title: str, user_access_token: str, folder_token: Optional[str] = None
    ) -> dict:
        """
        创建空白文档

        Args:
            title: 文档标题
            user_access_token: 用户访问凭证
            folder_token: 目标文件夹 token（可选）

        Returns:
            包含 document_id, revision_id, title 的字典
        """
        from lark_oapi.api.docx.v1 import (
            CreateDocumentRequest,
            CreateDocumentRequestBody,
            CreateDocumentResponse,
        )

        body = CreateDocumentRequestBody.builder().title(title)
        if folder_token:
            body = body.folder_token(folder_token)

        request = CreateDocumentRequest.builder().request_body(body.build()).build()
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: CreateDocumentResponse = self.client.docx.v1.document.create(request, option)

        if not response.success():
            self._log_error("docx.v1.document.create", response)
            raise RuntimeError(f"创建文档失败: {response.msg}")

        doc = response.data.document
        return {
            "document_id": doc.document_id,
            "revision_id": doc.revision_id,
            "title": doc.title,
        }

    def create_blocks(
            self,
            document_id: str,
            block_id: str,
            children: List[dict],
            user_access_token: str,
            index: int = -1,
    ) -> List[dict]:
        """
        在指定 Block 下创建子 Block (支持分批创建以绕过 50 个限制)

        Args:
            document_id: 文档 ID
            block_id: 父 Block ID（通常是 document_id 作为根节点）
            children: 子 Block 列表
            user_access_token: 用户访问凭证
            index: 插入位置，-1 表示末尾

        Returns:
            创建的 Block 列表
        """
        from lark_oapi.api.docx.v1 import (
            CreateDocumentBlockChildrenRequest,
            CreateDocumentBlockChildrenRequestBody,
            CreateDocumentBlockChildrenResponse,
        )
        all_created_children = []
        chunk_size = 50
        current_index = index

        for i in range(0, len(children), chunk_size):
            chunk = children[i: i + chunk_size]
            body_builder = CreateDocumentBlockChildrenRequestBody.builder().children(chunk)
            if current_index >= 0:
                body_builder = body_builder.index(current_index)

            request = (
                CreateDocumentBlockChildrenRequest.builder()
                .document_id(document_id)
                .block_id(block_id)
                .document_revision_id(-1)
                .request_body(body_builder.build())
                .build()
            )
            option = lark.RequestOption.builder().user_access_token(user_access_token).build()

            console.print(f"  [DEBUG] Sending chunk {i // chunk_size} (blocks {i} to {i + len(chunk) - 1})...")

            response: CreateDocumentBlockChildrenResponse = (
                self.client.docx.v1.document_block_children.create(request, option)
            )

            if not response.success():
                self._log_error("docx.v1.document_block_children.create", response)
                try:
                    chunk_json = json.dumps(chunk, ensure_ascii=True, indent=2)
                    console.print(f"  [ERROR] Failed chunk content:\n{chunk_json}")
                except Exception as e:
                    console.print(f"  [ERROR] Could not dump chunk: {e}")
                raise RuntimeError(f"创建 Block 失败: {response.msg}")

            try:
                data = json.loads(response.raw.content)
                created = data.get("data", {}).get("children", [])
                all_created_children.extend(created)
            except json.JSONDecodeError:
                pass

            if current_index >= 0:
                current_index += len(chunk)

        return all_created_children

    def update_block(
            self, document_id: str, block_id: str, update_body: dict, user_access_token: str
    ) -> dict:
        """
        更新单个 Block 内容

        Args:
            document_id: 文档 ID
            block_id: Block ID
            update_body: 更新内容（如 text, heading1 等）
            user_access_token: 用户访问凭证

        Returns:
            更新后的 Block
        """
        from lark_oapi.api.docx.v1 import (
            PatchDocumentBlockRequest,
            PatchDocumentBlockResponse,
        )

        request = (
            PatchDocumentBlockRequest.builder()
            .document_id(document_id)
            .block_id(block_id)
            .document_revision_id(-1)
            .request_body(update_body)
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: PatchDocumentBlockResponse = self.client.docx.v1.document_block.patch(
            request, option
        )

        if not response.success():
            self._log_error("docx.v1.document_block.patch", response)
            raise RuntimeError(f"更新 Block 失败: {response.msg}")

        data = json.loads(response.raw.content)
        return data.get("data", {}).get("block", {})

    def replace_image(
            self,
            document_id: str,
            block_id: str,
            file_token: str,
            user_access_token: str,
    ) -> dict:
        """
        使用 patch 接口替换图片内容
        """
        from lark_oapi.api.docx.v1 import (
            PatchDocumentBlockRequest,
            PatchDocumentBlockResponse,
            ReplaceImageRequest,
            UpdateBlockRequest,
        )

        request = (
            PatchDocumentBlockRequest.builder()
            .document_id(document_id)
            .block_id(block_id)
            .document_revision_id(-1)
            .request_body(
                UpdateBlockRequest.builder()
                .replace_image(ReplaceImageRequest.builder().token(file_token).build())
                .build()
            )
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: PatchDocumentBlockResponse = self.client.docx.v1.document_block.patch(
            request, option
        )

        if not response.success():
            self._log_error("docx.v1.document_block.patch.replace_image", response)
            raise RuntimeError(f"替换图片失败: {response.msg}")

        data = json.loads(response.raw.content)
        return data.get("data", {}).get("block", {})

    def batch_update_blocks(
            self, document_id: str, requests: List[dict], user_access_token: str
    ) -> List[dict]:
        """
        批量更新多个 Block

        Args:
            document_id: 文档 ID
            requests: 更新请求列表，每个包含 block_id 和更新内容
            user_access_token: 用户访问凭证

        Returns:
            更新后的 Block 列表
        """
        from lark_oapi.api.docx.v1 import (
            BatchUpdateDocumentBlockRequest,
            BatchUpdateDocumentBlockRequestBody,
            BatchUpdateDocumentBlockResponse,
        )

        request = (
            BatchUpdateDocumentBlockRequest.builder()
            .document_id(document_id)
            .document_revision_id(-1)
            .request_body(
                BatchUpdateDocumentBlockRequestBody.builder().requests(requests).build()
            )
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: BatchUpdateDocumentBlockResponse = (
            self.client.docx.v1.document_block.batch_update(request, option)
        )

        if not response.success():
            self._log_error("docx.v1.document_block.batch_update", response)
            raise RuntimeError(f"批量更新 Block 失败: {response.msg}")

        data = json.loads(response.raw.content)
        return data.get("data", {}).get("blocks", [])

    def delete_block(self, document_id: str, block_id: str, user_access_token: str) -> None:
        """
        删除指定的 Block

        Args:
            document_id: 文档 ID
            block_id: Block ID
            user_access_token: 用户访问凭证
        """
        requests = [{"delete_block": {"block_id": block_id}}]
        self.batch_update_blocks(document_id, requests, user_access_token)

    def convert_markdown(self, markdown_content: str, user_access_token: str) -> List[dict]:
        """
        将 Markdown 转换为飞书 Block 结构

        使用飞书原生 API 转换，比自定义转换器更可靠。

        Args:
            markdown_content: Markdown 内容
            user_access_token: 用户访问凭证

        Returns:
            Block 列表
        """
        from lark_oapi.api.docx.v1 import (
            ConvertDocumentRequest,
            ConvertDocumentRequestBody,
            ConvertDocumentResponse,
        )

        request = (
            ConvertDocumentRequest.builder()
            .request_body(
                ConvertDocumentRequestBody.builder()
                .content_type("markdown")
                .content(markdown_content)
                .build()
            )
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: ConvertDocumentResponse = self.client.docx.v1.document.convert(request, option)

        if not response.success():
            self._log_error("docx.v1.document.convert", response)
            raise RuntimeError(f"Markdown 转换失败: {response.msg}")

        data = json.loads(response.raw.content)
        return data.get("data", {}).get("children", [])

    def delete_blocks(
            self, document_id: str, block_id: str, start_index: int, end_index: int, user_access_token: str
    ) -> bool:
        """
        删除指定范围的子 Block

        Args:
            document_id: 文档 ID
            block_id: 父 Block ID
            start_index: 起始索引
            end_index: 结束索引
            user_access_token: 用户访问凭证

        Returns:
            是否成功
        """
        from lark_oapi.api.docx.v1 import (
            BatchDeleteDocumentBlockChildrenRequest,
            BatchDeleteDocumentBlockChildrenRequestBody,
            BatchDeleteDocumentBlockChildrenResponse,
        )

        request = (
            BatchDeleteDocumentBlockChildrenRequest.builder()
            .document_id(document_id)
            .block_id(block_id)
            .document_revision_id(-1)
            .request_body(
                BatchDeleteDocumentBlockChildrenRequestBody.builder()
                .start_index(start_index)
                .end_index(end_index)
                .build()
            )
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: BatchDeleteDocumentBlockChildrenResponse = (
            self.client.docx.v1.document_block_children.batch_delete(request, option)
        )

        if not response.success():
            self._log_error("docx.v1.document_block_children.batch_delete", response)
            return False

        return True

    def clear_document(
            self,
            document_id: str,
            user_access_token: str,
            batch_size: int = 200,
            max_rounds: int = 20,
    ) -> int:
        """
        清空文档根节点下的所有子 Block

        Args:
            document_id: 文档 ID
            user_access_token: 用户访问凭证
            batch_size: 单次删除的子块数量
            max_rounds: 最大删除轮次，避免死循环

        Returns:
            删除的块数量（近似值）
        """
        deleted_total = 0
        rounds = 0

        while rounds < max_rounds:
            rounds += 1
            blocks = self.get_document_block_list(document_id, user_access_token)
            if not blocks:
                break

            block_map = {b.block_id: b for b in blocks if getattr(b, "block_id", None)}
            root_block = block_map.get(document_id)
            if not root_block:
                root_block = next((b for b in blocks if getattr(b, "block_type", None) == 1), None)
            if not root_block:
                break

            root_id = root_block.block_id or document_id
            children = root_block.children or []
            if not children:
                break

            delete_count = min(len(children), batch_size)
            ok = self.delete_blocks(
                document_id=document_id,
                block_id=root_id,
                start_index=0,
                end_index=delete_count,
                user_access_token=user_access_token,
            )
            if not ok:
                break

            deleted_total += delete_count

        return deleted_total

    # ==========================================================================
    # 图片 & 附件
    # ==========================================================================
    def upload_image(
            self,
            file_path: str,
            parent_node: str,
            document_id: str,
            user_access_token: str,
    ) -> str:
        """
        上传本地图片到云空间

        Args:
            file_path: 本地图片路径
            parent_node: 父节点 token (通常是图片 block_id)
            document_id: 文档 ID（用于 drive_route_token）
            user_access_token: 用户访问凭证

        Returns:
            图片的 file_token
        """
        import mimetypes
        from lark_oapi.api.drive.v1 import (
            UploadAllMediaRequest,
            UploadAllMediaRequestBody,
            UploadAllMediaResponse,
        )

        p = Path(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "image/jpeg"

        def _try_upload(parent_type: str, node: str) -> Optional[str]:
            with open(file_path, "rb") as f:
                body_builder = (
                    UploadAllMediaRequestBody.builder()
                    .file_name(p.name)
                    .parent_type(parent_type)
                    .parent_node(node)
                    .size(p.stat().st_size)
                    .file(f)
                )
                if node != document_id:
                    body_builder = body_builder.extra(
                        json.dumps({"drive_route_token": document_id})
                    )
                request = (
                    UploadAllMediaRequest.builder()
                    .request_body(body_builder.build())
                    .build()
                )
                option = lark.RequestOption.builder().user_access_token(user_access_token).build()
                response: UploadAllMediaResponse = self.client.drive.v1.media.upload_all(request, option)
            if not response.success():
                self._log_error("drive.v1.media.upload_all", response)
                return None
            return response.data.file_token

        token = _try_upload("docx_image", parent_node)
        if token:
            return token

        token = _try_upload("doc_image", document_id)
        if token:
            return token

        raise RuntimeError(f"上传图片失败 ({p.name})")
    def get_image(self, file_token: str, user_access_token: str) -> Optional[str]:
        """
        下载云文档中的图片

        Args:
            file_token: 图片的 token
            user_access_token: 用户访问凭证

        Returns:
            保存后的文件路径
        """
        request = DownloadMediaRequest.builder().file_token(file_token).build()
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: DownloadMediaResponse = self.client.drive.v1.media.download(request, option)

        if not response.success():
            self._log_error("drive.v1.media.download", response)
            return None

        # 推断扩展名
        extension = ".png"
        if hasattr(response, "file_name") and response.file_name:
            if "." in response.file_name:
                extension = f".{response.file_name.split('.')[-1]}"

        # 保存到临时目录
        file_path = self.temp_dir / f"{file_token}{extension}"
        file_path.write_bytes(response.file.read())
        return str(file_path)

    def get_whiteboard(self, whiteboard_id: str, user_access_token: str) -> Optional[str]:
        """
        导出画板为图片

        Args:
            whiteboard_id: 画板 ID
            user_access_token: 用户访问凭证

        Returns:
            保存后的文件路径
        """
        request = DownloadAsImageWhiteboardRequest.builder().whiteboard_id(whiteboard_id).build()
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: DownloadAsImageWhiteboardResponse = self.client.board.v1.whiteboard.download_as_image(
            request, option
        )

        if not response.success():
            self._log_error("board.v1.whiteboard.download_as_image", response)
            return None

        file_path = self.temp_dir / f"{whiteboard_id}.png"
        file_path.write_bytes(response.file.read())
        return str(file_path)

    def get_file_download_url(self, file_token: str, user_access_token: str) -> Optional[str]:
        """
        获取文件临时下载 URL

        Args:
            file_token: 文件 token
            user_access_token: 用户访问凭证

        Returns:
            临时下载 URL（有效期约 1 小时）
        """
        from lark_oapi.api.drive.v1 import (
            BatchGetTmpDownloadUrlMediaRequest,
            BatchGetTmpDownloadUrlMediaResponse,
        )

        request = (
            BatchGetTmpDownloadUrlMediaRequest.builder()
            .file_tokens([file_token])
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: BatchGetTmpDownloadUrlMediaResponse = self.client.drive.v1.media.batch_get_tmp_download_url(
            request, option
        )

        if not response.success():
            self._log_error("drive.v1.media.batch_get_tmp_download_url", response)
            return None

        # 从响应中提取下载 URL
        if response.data and response.data.tmp_download_urls:
            for item in response.data.tmp_download_urls:
                if item.file_token == file_token:
                    return item.tmp_download_url
        return None

    # ==========================================================================
    # 电子表格
    # ==========================================================================
    def get_spreadsheet_info(self, spreadsheet_token: str, user_access_token: str) -> dict:
        """
        获取电子表格基本信息（包含标题）

        Args:
            spreadsheet_token: 电子表格 token
            user_access_token: 用户访问凭证

        Returns:
            包含 spreadsheet_token, title 的字典
        """
        from lark_oapi.api.sheets.v3 import GetSpreadsheetRequest, GetSpreadsheetResponse

        request = GetSpreadsheetRequest.builder().spreadsheet_token(spreadsheet_token).build()
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: GetSpreadsheetResponse = self.client.sheets.v3.spreadsheet.get(request, option)

        if not response.success():
            self._log_error("sheets.v3.spreadsheet.get", response)
            return {"spreadsheet_token": spreadsheet_token, "title": spreadsheet_token}

        sheet = response.data.spreadsheet
        return {
            "spreadsheet_token": sheet.token,
            "title": sheet.title or spreadsheet_token,
        }

    def get_sheet_list(self, spreadsheet_token: str, user_access_token: str) -> Optional[List[Sheet]]:
        """
        获取电子表格的所有工作表

        Args:
            spreadsheet_token: 电子表格 token
            user_access_token: 用户访问凭证

        Returns:
            工作表列表
        """
        request = QuerySpreadsheetSheetRequest.builder().spreadsheet_token(spreadsheet_token).build()
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: QuerySpreadsheetSheetResponse = self.client.sheets.v3.spreadsheet_sheet.query(request, option)

        if not response.success():
            self._log_error("sheets.v3.spreadsheet_sheet.query", response)
            raise RuntimeError("获取工作表列表失败")

        return response.data.sheets

    def get_sheet_metadata(self, spreadsheet_token: str, user_access_token: str) -> Optional[list]:
        """
        获取电子表格元数据（包含 Block 信息）

        Args:
            spreadsheet_token: 电子表格 token
            user_access_token: 用户访问凭证

        Returns:
            工作表元数据列表
        """
        request = (
            lark.BaseRequest.builder()
            .http_method(lark.HttpMethod.GET)
            .uri(f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo")
            .token_types({lark.AccessTokenType.USER})
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: BaseResponse = self.client.request(request, option)

        if not response.success():
            self._log_error("sheets.v2.metainfo", response)
            return None

        try:
            content = response.raw.content.decode("utf-8")
            resp_json = json.loads(content)
            return resp_json.get("data", {}).get("sheets", [])
        except Exception as e:
            console.print(f"[red]解析工作表元数据失败: {e}[/red]")
            return None

    def get_sheet(
            self,
            sheet_token: str,
            sheet_id: str,
            user_access_token: str,
            table_mode: TableMode,
    ) -> Optional[str]:
        """
        获取电子表格数据并转换为 Markdown/HTML

        Args:
            sheet_token: 电子表格 token
            sheet_id: 工作表 ID
            user_access_token: 用户访问凭证
            table_mode: 输出格式

        Returns:
            Markdown 或 HTML 表格字符串
        """
        request = (
            lark.BaseRequest.builder()
            .http_method(lark.HttpMethod.GET)
            .uri(f"/open-apis/sheets/v2/spreadsheets/{sheet_token}/values/{sheet_id}")
            .token_types({lark.AccessTokenType.USER})
            .build()
        )
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: BaseResponse = self.client.request(request, option)

        if not response.success():
            self._log_error("sheets.v2.values", response)
            return None

        try:
            content = response.raw.content.decode("utf-8")
            resp_json = json.loads(content)
            values = resp_json.get("data", {}).get("valueRange", {}).get("values", [])

            if not values:
                return ""

            if table_mode == TableMode.MARKDOWN:
                return convert_to_markdown(values)
            else:
                return convert_to_html(values)

        except Exception as e:
            console.print(f"[red]解析工作表数据失败: {e}[/red]")
            return None

    # ==========================================================================
    # 多维表格
    # ==========================================================================
    def get_bitable_info(self, app_token: str, user_access_token: str) -> dict:
        """
        获取多维表格基本信息（包含标题）

        Args:
            app_token: 多维表格 app_token
            user_access_token: 用户访问凭证

        Returns:
            包含 app_token, name (标题) 的字典
        """

        request = GetAppRequest.builder().app_token(app_token).build()
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: GetAppResponse = self.client.bitable.v1.app.get(request, option)

        if not response.success():
            self._log_error("bitable.v1.app.get", response)
            return {"app_token": app_token, "title": app_token}

        app = response.data.app
        return {
            "app_token": app.app_token,
            "title": app.name or app_token,
        }

    def get_bitable_table_list(self, app_token: str, user_access_token: str) -> List[AppTable]:
        """
        获取多维表格的所有数据表

        Args:
            app_token: 多维表格 app_token
            user_access_token: 用户访问凭证

        Returns:
            数据表列表
        """
        request = ListAppTableRequest.builder().app_token(app_token).page_size(20).build()
        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: ListAppTableResponse = self.client.bitable.v1.app_table.list(request, option)

        if not response.success():
            self._log_error("bitable.v1.app_table.list", response)
            raise RuntimeError("获取多维表格列表失败")

        return response.data.items

    def get_bitable(
            self,
            app_token: str,
            table_id: str,
            user_access_token: str,
            table_mode: TableMode,
            view_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        获取多维表格数据并转换为 Markdown/HTML

        Args:
            app_token: 多维表格 app_token
            table_id: 数据表 ID
            user_access_token: 用户访问凭证
            table_mode: 输出格式
            view_id: 视图 ID（可选）

        Returns:
            Markdown 或 HTML 表格字符串
        """
        try:
            # 1. 获取表头
            headers = self._get_bitable_headers(app_token, table_id, view_id, user_access_token)
            if not headers:
                raise RuntimeError(f"多维表格 {app_token}/{table_id} 没有字段")

            # 2. 获取记录
            records = self._get_bitable_records(app_token, table_id, view_id, user_access_token)

            # 3. 构建矩阵
            matrix = [[header.field_name for header in headers]]

            for record in records:
                row_values = []
                fields_data = record.fields
                for header in headers:
                    val = fields_data.get(header.field_name, "")
                    parsed_val = self._parse_bitable_field_value(header, val)
                    row_values.append(parsed_val)
                matrix.append(row_values)

            # 4. 转换格式
            if table_mode == TableMode.MARKDOWN:
                return convert_to_markdown(matrix)
            else:
                return convert_to_html(matrix)

        except Exception as e:
            console.print(f"[red]处理多维表格失败: {e}[/red]")
            return None

    def _get_bitable_headers(
            self,
            app_token: str,
            table_id: str,
            view_id: Optional[str],
            user_access_token: str,
    ) -> Optional[List[AppTableFieldForList]]:
        """获取多维表格字段列表"""
        request = (
            ListAppTableFieldRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .page_size(100)
            .build()
        )

        if view_id:
            request.view_id = view_id
            request.add_query("view_id", view_id)

        option = lark.RequestOption.builder().user_access_token(user_access_token).build()
        response: ListAppTableFieldResponse = self.client.bitable.v1.app_table_field.list(request, option)

        if not response.success():
            self._log_error("bitable.v1.app_table_field.list", response)
            return []

        return response.data.items

    def _get_bitable_records(
            self,
            app_token: str,
            table_id: str,
            view_id: Optional[str],
            user_access_token: str,
    ) -> List[Any]:
        """获取多维表格所有记录"""
        all_records = []
        page_token = None
        has_more = True

        option = lark.RequestOption.builder().user_access_token(user_access_token).build()

        while has_more:
            request = (
                SearchAppTableRecordRequest.builder()
                .app_token(app_token)
                .table_id(table_id)
                .user_id_type("user_id")
                .page_size(100)
                .request_body(SearchAppTableRecordRequestBody.builder().build())
                .build()
            )

            if view_id:
                request.view_id = view_id
                request.add_query("view_id", view_id)

            if page_token:
                request.page_token = page_token
                request.add_query("page_token", page_token)

            response: SearchAppTableRecordResponse = self.client.bitable.v1.app_table_record.search(
                request, option
            )

            if not response.success():
                self._log_error("bitable.v1.app_table_record.search", response)
                return []

            if response.data.items:
                all_records.extend(response.data.items)

            has_more = response.data.has_more
            page_token = response.data.page_token

        return all_records

    @staticmethod
    def _parse_bitable_field_value(header: AppTableFieldForList, value: Any) -> str:
        """解析多维表格字段值"""
        if value is None:
            return ""

        # 日期时间类型
        if header.ui_type == "DateTime":
            try:
                return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                return str(value)

        def extract_text(data):
            texts = []
            for item in data:
                if isinstance(item, dict):
                    if "text" in item:
                        texts.append(item["text"])
                    elif "name" in item:
                        texts.append(item["name"])
                    elif "url" in item:
                        texts.append(item["url"])
                    elif "full_name" in item:
                        texts.append(item["full_name"])
                    else:
                        texts.append(str(item))
                else:
                    texts.append(str(item))
            return ", ".join(texts)

        if isinstance(value, list):
            return extract_text(value)

        if isinstance(value, dict):
            if "text" in value:
                return value["text"]
            if "name" in value:
                return value["name"]
            if "value" in value:
                return extract_text(value["value"])
            return json.dumps(value, ensure_ascii=False)

        return str(value)

    @staticmethod
    def _log_error(api_name: str, response):
        """统一错误日志"""
        try:
            content = json.loads(response.raw.content)
            formatted = json.dumps(content, indent=2, ensure_ascii=False)
        except Exception:
            formatted = str(response.raw.content)

        console.print(
            f"[red]API 调用失败: {api_name}[/red]\n"
            f"  status: {response.raw.status_code}\n"
            f"  code: {response.code}\n"
            f"  msg: {response.msg}\n"
            f"  log_id: {response.get_log_id()}\n"
            f"  response: {formatted}"
        )
