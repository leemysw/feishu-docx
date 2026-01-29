# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：main.py
# @Date   ：2026/01/28 19:00
# @Author ：leemysw
# 2025/01/09 18:30   Create
# 2026/01/28 11:10   Support folder url parsing
# 2026/01/28 12:05   Use safe console output
# 2026/01/28 16:00   Add whiteboard metadata export option
# 2026/01/28 18:00   Add workspace schema and wiki batch export commands
# 2026/01/28 19:00   Fix wiki export: support old doc format, preserve hierarchy
# =====================================================
"""
[INPUT]: 依赖 typer 的 CLI 框架，依赖 feishu_docx.core.exporter 的导出器
[OUTPUT]: 对外提供 app (Typer 应用) 作为 CLI 入口
[POS]: cli 模块的主入口，定义所有命令
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer
from rich.panel import Panel
from rich.table import Table

from feishu_docx import __version__
from feishu_docx.auth.oauth import OAuth2Authenticator
from feishu_docx.core.exporter import FeishuExporter
from feishu_docx.utils.config import AppConfig, get_config_dir
from feishu_docx.utils.console import get_console

console = get_console()

# ==============================================================================
# 创建 Typer 应用
# ==============================================================================
app = typer.Typer(
    name="feishu-docx",
    help="🚀 飞书云文档导出 Markdown 工具",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ==============================================================================
# 辅助函数
# ==============================================================================
def get_credentials(
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    获取凭证（优先级：命令行参数 > 环境变量 > 配置文件）

    Returns:
        (app_id, app_secret)
    """
    # 1. 命令行参数优先
    final_app_id = app_id
    final_app_secret = app_secret

    # 2. 环境变量次之
    if not final_app_id:
        final_app_id = os.getenv("FEISHU_APP_ID")
    if not final_app_secret:
        final_app_secret = os.getenv("FEISHU_APP_SECRET")

    # 3. 配置文件最后
    if not final_app_id or not final_app_secret:
        config = AppConfig.load()
        if not final_app_id:
            final_app_id = config.app_id
        if not final_app_secret:
            final_app_secret = config.app_secret

    return final_app_id, final_app_secret


def normalize_folder_token(folder: Optional[str]) -> Optional[str]:
    if not folder:
        return None
    if re.match(r"^[A-Za-z0-9]+$", folder):
        return folder
    try:
        parsed = urlparse(folder)
        if not parsed.path:
            return folder
        match = re.search(r"/drive/folder/([A-Za-z0-9]+)", parsed.path)
        if match:
            return match.group(1)
    except Exception:
        return folder
    return folder


# ==============================================================================
# 版本回调
# ==============================================================================
def version_callback(value: bool):
    if value:
        console.print(f"[bold blue]feishu-docx[/bold blue] version [green]{__version__}[/green]")
        raise typer.Exit()


# ==============================================================================
# 主回调
# ==============================================================================
@app.callback()
def main(
        version: bool = typer.Option(
            None,
            "--version",
            "-v",
            help="显示版本号",
            callback=version_callback,
            is_eager=True,
        ),
):
    """
    🚀 飞书云文档导出 Markdown 工具

    支持导出云文档、电子表格、多维表格、知识库文档。
    """
    pass


# ==============================================================================
# export 命令
# ==============================================================================
@app.command()
def export(
        url: str = typer.Argument(..., help="飞书文档 URL"),
        output: Path = typer.Option(
            Path("./output"),
            "-o",
            "--output",
            help="输出目录",
            file_okay=False,
            dir_okay=True,
        ),
        filename: Optional[str] = typer.Option(
            None,
            "-n",
            "--name",
            help="输出文件名（不含扩展名）",
        ),
        token: Optional[str] = typer.Option(
            None,
            "-t",
            "--token",
            envvar="FEISHU_ACCESS_TOKEN",
            help="用户访问凭证（或设置环境变量 FEISHU_ACCESS_TOKEN）",
        ),
        app_id: Optional[str] = typer.Option(
            None,
            "--app-id",
            help="飞书应用 App ID（覆盖配置文件）",
        ),
        app_secret: Optional[str] = typer.Option(
            None,
            "--app-secret",
            help="飞书应用 App Secret（覆盖配置文件）",
        ),
        table_format: str = typer.Option(
            "md",
            "--table",
            help="表格输出格式: html / md",
        ),
        lark: bool = typer.Option(
            False,
            "--lark",
            help="使用 Lark (海外版)",
        ),
        stdout: bool = typer.Option(
            False,
            "--stdout",
            "-c",
            help="直接输出内容到 stdout（不保存文件，适合 AI Agent 使用）",
        ),
        with_block_ids: bool = typer.Option(
            False,
            "--with-block-ids",
            "-b",
            help="在导出的 Markdown 中嵌入 Block ID 注释（用于后续更新文档）",
        ),
        export_board_metadata: bool = typer.Option(
            False,
            "--export-board-metadata",
            help="导出画板节点元数据（包含位置、大小、类型等信息）",
        ),
):
    """
    [green]▶[/] 导出飞书文档为 Markdown


    示例:

        # 使用已配置的凭证导出（推荐，需先运行 feishu-docx config set）\n
        feishu-docx export "https://xxx.feishu.cn/docx/xxx"

        # 使用 Token (如: user_access_token) 导出 \n
        feishu-docx export "https://xxx.feishu.cn/docx/xxx" -t your_token

        # 使用 OAuth 授权（覆盖配置）\n
        feishu-docx export "https://xxx.feishu.cn/docx/xxx" --app-id xxx --app-secret xxx

        # 导出到指定目录 \n
        feishu-docx export "https://xxx.feishu.cn/docx/xxx" -o ./docs -n my_doc

        # 直接输出内容（适合 AI Agent）\n
        feishu-docx export "https://xxx.feishu.cn/docx/xxx" --stdout

        # 同时导出画板图片和元数据 \n
        feishu-docx export "https://xxx.feishu.cn/docx/xxx" --export-board-metadata
    """
    try:
        # 创建导出器
        if token:
            exporter = FeishuExporter.from_token(token)
        else:
            # 获取凭证（命令行参数 > 环境变量 > 配置文件）
            final_app_id, final_app_secret = get_credentials(app_id, app_secret)

            if final_app_id and final_app_secret:
                exporter = FeishuExporter(app_id=final_app_id, app_secret=final_app_secret, is_lark=lark)
            else:
                console.print(
                    "[red]❌ 需要提供 Token 或 OAuth 凭证[/red]\n\n"
                    "方式一：先配置凭证（推荐）\n"
                    "  [cyan]feishu-docx config set --app-id xxx --app-secret xxx[/cyan]\n\n"
                    "方式二：使用 Token (如: user_access_token)\n"
                    "  [cyan]feishu-docx export URL -t your_token[/cyan]\n\n"
                    "方式三：命令行传入\n"
                    "  [cyan]feishu-docx export URL --app-id xxx --app-secret xxx[/cyan]"
                )
                raise typer.Exit(1)

        # 执行导出
        if stdout:
            # 直接输出内容到 stdout
            content = exporter.export_content(
                url=url,
                table_format=table_format,  # type: ignore
                export_board_metadata=export_board_metadata,
            )
            print(content)
        else:
            # 保存到文件
            output_path = exporter.export(
                url=url,
                output_dir=output,
                filename=filename,
                table_format=table_format,  # type: ignore
                with_block_ids=with_block_ids,
                export_board_metadata=export_board_metadata,
            )
            console.print(Panel(f"✅ 导出完成: [green]{output_path}[/green]", border_style="green"))

    except ValueError as e:
        console.print(f"[red]❌ 错误: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ 导出失败: {e}[/red]")
        raise typer.Exit(1)


# ==============================================================================
# create 命令 - 创建文档
# ==============================================================================
@app.command()
def create(
        title: str = typer.Argument(..., help="文档标题"),
        content: Optional[str] = typer.Option(
            None,
            "-c",
            "--content",
            help="Markdown 内容字符串",
        ),
        file: Optional[Path] = typer.Option(
            None,
            "-f",
            "--file",
            help="Markdown 文件路径",
            exists=True,
        ),
        folder: Optional[str] = typer.Option(
            None,
            "--folder",
            help="目标文件夹 token",
        ),
        token: Optional[str] = typer.Option(
            None,
            "-t",
            "--token",
            envvar="FEISHU_ACCESS_TOKEN",
            help="用户访问凭证",
        ),
        app_id: Optional[str] = typer.Option(None, "--app-id", help="飞书应用 App ID"),
        app_secret: Optional[str] = typer.Option(None, "--app-secret", help="飞书应用 App Secret"),
        lark: bool = typer.Option(False, "--lark", help="使用 Lark (海外版)"),
):
    """
    [green]▶[/] 创建飞书文档

    示例:

        # 创建空白文档\\n
        feishu-docx create "我的笔记"

        # 创建文档并写入 Markdown 内容\\n
        feishu-docx create "会议记录" -c "# 会议纪要\\n\\n- 议题一\\n- 议题二"

        # 从 Markdown 文件创建文档\\n
        feishu-docx create "周报" -f ./weekly_report.md
    """
    try:
        from feishu_docx.core.writer import FeishuWriter

        # 获取凭证
        if token:
            from feishu_docx import FeishuExporter
            exporter = FeishuExporter.from_token(token)
            access_token = token
        else:
            final_app_id, final_app_secret = get_credentials(app_id, app_secret)
            if not final_app_id or not final_app_secret:
                console.print("[red]❌ 需要提供凭证，请运行 feishu-docx config set[/red]")
                raise typer.Exit(1)
            from feishu_docx import FeishuExporter
            exporter = FeishuExporter(app_id=final_app_id, app_secret=final_app_secret, is_lark=lark)
            access_token = exporter.get_access_token()

        writer = FeishuWriter(sdk=exporter.sdk)

        # 创建文档
        doc = writer.create_document(
            title=title,
            content=content,
            file_path=file,
            folder_token=normalize_folder_token(folder),
            user_access_token=access_token,
        )

        console.print(Panel(
            f"✅ 创建成功!\n\n"
            f"[blue]文档 ID:[/blue] {doc['document_id']}\n"
            f"[blue]链接:[/blue] {doc['url']}",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[red]❌ 创建失败: {e}[/red]")
        raise typer.Exit(1)


# ==============================================================================
# write 命令 - 向文档写入内容
# ==============================================================================
@app.command()
def write(
        url: str = typer.Argument(..., help="飞书文档 URL"),
        content: Optional[str] = typer.Option(
            None,
            "-c",
            "--content",
            help="Markdown 内容字符串",
        ),
        file: Optional[Path] = typer.Option(
            None,
            "-f",
            "--file",
            help="Markdown 文件路径",
            exists=True,
        ),
        token: Optional[str] = typer.Option(
            None,
            "-t",
            "--token",
            envvar="FEISHU_ACCESS_TOKEN",
            help="用户访问凭证",
        ),
        app_id: Optional[str] = typer.Option(None, "--app-id", help="飞书应用 App ID"),
        app_secret: Optional[str] = typer.Option(None, "--app-secret", help="飞书应用 App Secret"),
        lark: bool = typer.Option(False, "--lark", help="使用 Lark (海外版)"),
):
    """
    [green]▶[/] 向飞书文档追加 Markdown 内容

    示例:

        # 追加 Markdown 内容\\n
        feishu-docx write "https://xxx.feishu.cn/docx/xxx" -c "## 新章节\\n\\n内容"

        # 从文件追加内容\\n
        feishu-docx write "https://xxx.feishu.cn/docx/xxx" -f ./content.md
    """
    if not content and not file:
        console.print("[red]❌ 必须提供 -c/--content 或 -f/--file[/red]")
        raise typer.Exit(1)

    try:
        from feishu_docx.core.writer import FeishuWriter
        from feishu_docx import FeishuExporter

        # 获取凭证
        if token:
            exporter = FeishuExporter.from_token(token)
            access_token = token
        else:
            final_app_id, final_app_secret = get_credentials(app_id, app_secret)
            if not final_app_id or not final_app_secret:
                console.print("[red]❌ 需要提供凭证[/red]")
                raise typer.Exit(1)
            exporter = FeishuExporter(app_id=final_app_id, app_secret=final_app_secret, is_lark=lark)
            access_token = exporter.get_access_token()

        # 解析 URL 获取 document_id
        doc_info = exporter.parse_url(url)
        if doc_info.doc_type != "docx":
            console.print(f"[red]❌ 只支持 docx 类型文档，当前类型: {doc_info.doc_type}[/red]")
            raise typer.Exit(1)

        writer = FeishuWriter(sdk=exporter.sdk)

        # 写入内容
        blocks = writer.write_content(
            document_id=doc_info.doc_id,
            content=content,
            file_path=file,
            user_access_token=access_token,
        )

        console.print(Panel(f"✅ 写入成功! 添加了 {len(blocks)} 个 Block", border_style="green"))

    except Exception as e:
        console.print(f"[red]❌ 写入失败: {e}[/red]")
        raise typer.Exit(1)


# ==============================================================================
# update 命令 - 更新指定 Block
# ==============================================================================
@app.command()
def update(
        url: str = typer.Argument(..., help="飞书文档 URL"),
        block_id: str = typer.Option(..., "-b", "--block-id", help="Block ID (从 --with-block-ids 导出获取)"),
        content: str = typer.Option(..., "-c", "--content", help="新的文本内容"),
        token: Optional[str] = typer.Option(
            None,
            "-t",
            "--token",
            envvar="FEISHU_ACCESS_TOKEN",
            help="用户访问凭证",
        ),
        app_id: Optional[str] = typer.Option(None, "--app-id", help="飞书应用 App ID"),
        app_secret: Optional[str] = typer.Option(None, "--app-secret", help="飞书应用 App Secret"),
        lark: bool = typer.Option(False, "--lark", help="使用 Lark (海外版)"),
):
    """
    [green]▶[/] 更新飞书文档中指定 Block 的内容

    示例:

        # 先导出获取 Block ID\\n
        feishu-docx export "https://xxx.feishu.cn/docx/xxx" --with-block-ids

        # 然后更新指定 Block\\n
        feishu-docx update "https://xxx.feishu.cn/docx/xxx" -b blk123abc -c "更新后的内容"
    """
    try:
        from feishu_docx.core.writer import FeishuWriter
        from feishu_docx import FeishuExporter

        # 获取凭证
        if token:
            exporter = FeishuExporter.from_token(token)
            access_token = token
        else:
            final_app_id, final_app_secret = get_credentials(app_id, app_secret)
            if not final_app_id or not final_app_secret:
                console.print("[red]❌ 需要提供凭证[/red]")
                raise typer.Exit(1)
            exporter = FeishuExporter(app_id=final_app_id, app_secret=final_app_secret, is_lark=lark)
            access_token = exporter.get_access_token()

        # 解析 URL 获取 document_id
        doc_info = exporter.parse_url(url)

        writer = FeishuWriter(sdk=exporter.sdk)

        # 更新 Block
        writer.update_block(
            document_id=doc_info.doc_id,
            block_id=block_id,
            content=content,
            user_access_token=access_token,
        )

        console.print(Panel(f"✅ Block [cyan]{block_id}[/cyan] 更新成功!", border_style="green"))

    except Exception as e:
        console.print(f"[red]❌ 更新失败: {e}[/red]")
        raise typer.Exit(1)


# ==============================================================================
# export-workspace-schema 命令 - 导出数据库结构
# ==============================================================================
@app.command()
def export_workspace_schema(
        workspace_id: str = typer.Argument(..., help="工作空间 ID"),
        output: Path = typer.Option(
            Path("./database_schema.md"),
            "-o",
            "--output",
            help="输出文件路径",
        ),
        token: Optional[str] = typer.Option(
            None,
            "-t",
            "--token",
            envvar="FEISHU_ACCESS_TOKEN",
            help="用户访问凭证",
        ),
        app_id: Optional[str] = typer.Option(None, "--app-id", help="飞书应用 App ID"),
        app_secret: Optional[str] = typer.Option(None, "--app-secret", help="飞书应用 App Secret"),
        lark: bool = typer.Option(False, "--lark", help="使用 Lark (海外版)"),
):
    """
    [green]▶[/] 导出数据库结构为 Markdown

    示例:

        # 导出工作空间数据库结构\\n
        feishu-docx export-workspace-schema <workspace_id>

        # 指定输出文件\\n
        feishu-docx export-workspace-schema <workspace_id> -o schema.md
    """
    try:
        # 获取凭证
        if token:
            exporter = FeishuExporter.from_token(token)
            access_token = token
        else:
            final_app_id, final_app_secret = get_credentials(app_id, app_secret)
            if not final_app_id or not final_app_secret:
                console.print("[red]❌ 需要提供凭证[/red]")
                raise typer.Exit(1)
            exporter = FeishuExporter(app_id=final_app_id, app_secret=final_app_secret, is_lark=lark)
            access_token = exporter.get_access_token()

        console.print(f"[blue]> 工作空间 ID:[/blue] {workspace_id}")
        console.print("[yellow]> 正在获取数据表列表...[/yellow]")

        # 获取所有数据表
        tables = exporter.sdk.get_all_workspace_tables(
            workspace_id=workspace_id,
            user_access_token=access_token,
        )

        if not tables:
            console.print("[yellow]⚠ 未找到数据表[/yellow]")
            raise typer.Exit(0)

        console.print(f"[green]✓ 找到 {len(tables)} 个数据表[/green]")

        # 生成 Markdown
        markdown_lines = [
            "# 工作空间数据库结构",
            "",
            f"**工作空间 ID**: `{workspace_id}`",
            f"**数据表数量**: {len(tables)}",
            "",
        ]

        for table in tables:
            table_name = table.get("name", "")
            description = table.get("description", "")
            columns = table.get("columns", [])

            markdown_lines.extend([
                f"## 📋 {table_name}",
                "",
            ])

            if description:
                markdown_lines.extend([f"> {description}", ""])

            markdown_lines.extend([
                "| 列名 | 类型 | 主键 | 唯一 | 自增 | 数组 | 允许空 | 默认值 | 描述 |",
                "|------|------|------|------|------|------|--------|--------|------|",
            ])

            for col in columns:
                row = (
                    f"| {col.get('name', '')} "
                    f"| {col.get('data_type', '')} "
                    f"| {'✓' if col.get('is_primary_key') else ''} "
                    f"| {'✓' if col.get('is_unique') else ''} "
                    f"| {'✓' if col.get('is_auto_increment') else ''} "
                    f"| {'✓' if col.get('is_array') else ''} "
                    f"| {'✓' if col.get('is_allow_null') else ''} "
                    f"| {col.get('default_value', '')} "
                    f"| {col.get('description', '')} |"
                )
                markdown_lines.append(row)

            markdown_lines.append("")

        # 保存文件
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(markdown_lines), encoding="utf-8")

        console.print(Panel(f"✅ 数据库结构已导出: [green]{output}[/green]", border_style="green"))

    except Exception as e:
        console.print(f"[red]❌ 导出失败: {e}[/red]")
        raise typer.Exit(1)


# ==============================================================================
# export-wiki-space 命令 - 批量导出知识空间
# ==============================================================================
@app.command()
def export_wiki_space(
        space_id_or_url: str = typer.Argument(..., help="知识空间 ID、Wiki URL 或 my_library"),
        output: Path = typer.Option(
            Path("./wiki_export"),
            "-o",
            "--output",
            help="输出目录",
        ),
        parent_node: Optional[str] = typer.Option(
            None,
            "--parent-node",
            help="父节点 token（不传则导出根节点下所有文档）",
        ),
        max_depth: int = typer.Option(
            3,
            "--max-depth",
            help="最大遍历深度",
        ),
        token: Optional[str] = typer.Option(
            None,
            "-t",
            "--token",
            envvar="FEISHU_ACCESS_TOKEN",
            help="用户访问凭证",
        ),
        app_id: Optional[str] = typer.Option(None, "--app-id", help="飞书应用 App ID"),
        app_secret: Optional[str] = typer.Option(None, "--app-secret", help="飞书应用 App Secret"),
        lark: bool = typer.Option(False, "--lark", help="使用 Lark (海外版)"),
):
    """
    [green]▶[/] 批量导出知识空间下的所有文档

    支持直接输入 Wiki URL，自动提取知识空间 ID。

    示例:

        # 使用 Wiki URL（自动提取 space_id）\\n
        feishu-docx export-wiki-space "https://my.feishu.cn/wiki/<token>"

        # 直接使用知识空间 ID\\n
        feishu-docx export-wiki-space <space_id>

        # 导出我的文档库\\n
        feishu-docx export-wiki-space my_library -o ./my_docs

        # 限制遍历深度\\n
        feishu-docx export-wiki-space my_library --max-depth 2
    """
    try:
        # 获取凭证
        if token:
            exporter = FeishuExporter.from_token(token)
            access_token = token
        else:
            final_app_id, final_app_secret = get_credentials(app_id, app_secret)
            if not final_app_id or not final_app_secret:
                console.print("[red]❌ 需要提供凭证[/red]")
                raise typer.Exit(1)
            exporter = FeishuExporter(app_id=final_app_id, app_secret=final_app_secret, is_lark=lark)
            access_token = exporter.get_access_token()

        # 解析输入参数，支持 URL、space_id 或 my_library
        space_id = space_id_or_url

        if space_id_or_url.startswith(("http://", "https://")):
            # 输入是 URL，解析并获取 space_id
            console.print("[yellow]> 检测到 Wiki URL，正在自动提取知识空间 ID...[/yellow]")

            try:
                doc_info = exporter.parse_url(space_id_or_url)
            except ValueError as e:
                console.print(f"[red]❌ URL 格式错误: {e}[/red]")
                raise typer.Exit(1)

            if doc_info.doc_type != "wiki":
                console.print(
                    f"[red]❌ 输入的不是 Wiki 链接（类型: {doc_info.doc_type}）[/red]\n"
                    f"[yellow]💡 提示: 请提供 Wiki URL 或直接使用 space_id[/yellow]"
                )
                raise typer.Exit(1)

            node_token = doc_info.doc_id
            console.print(f"[dim]  节点 Token: {node_token}[/dim]")

            # 获取节点信息并提取 space_id
            node_info = exporter.sdk.get_wiki_node_by_token(
                token=node_token,
                user_access_token=access_token,
            )

            if not node_info or not node_info.get("space_id"):
                console.print("[red]❌ 无法获取知识空间信息[/red]")
                raise typer.Exit(1)

            space_id = node_info.get("space_id")
            console.print(f"[green]✓ 成功提取知识空间 ID:[/green] {space_id}")

            if node_info.get("title"):
                console.print(f"[dim]  页面标题: {node_info.get('title')}[/dim]")

        console.print(f"[blue]> 知识空间 ID:[/blue] {space_id}")
        console.print(f"[blue]> 输出目录:[/blue] {output}")
        console.print(f"[blue]> 最大深度:[/blue] {max_depth}")

        # 创建输出目录
        output.mkdir(parents=True, exist_ok=True)

        exported_count = 0
        failed_count = 0

        # 确定域名
        domain = "larksuite.com" if lark else "my.feishu.cn"

        # 递归遍历节点
        def traverse_nodes(parent_token: Optional[str] = None, depth: int = 0, current_path: Path = output):
            nonlocal exported_count, failed_count

            if depth > max_depth:
                return

            console.print(f"[yellow]> 正在遍历第 {depth} 层: {current_path.name}...[/yellow]")

            # 获取子节点列表
            nodes = exporter.sdk.get_all_wiki_space_nodes(
                space_id=space_id,
                user_access_token=access_token,
                parent_node_token=parent_token,
            )

            if not nodes:
                return

            for node in nodes:
                node_token = node.get("node_token")
                obj_type = node.get("obj_type")
                obj_token = node.get("obj_token")
                title = node.get("title", "untitled")
                has_child = node.get("has_child", False)

                # 清理文件名中的非法字符
                safe_title = title.replace("/", "_").replace("\\", "_")

                # 判断是否为文档类型
                if obj_type in ["doc", "docx", "sheet", "bitable"]:
                    try:
                        # 构建文档 URL
                        url = f"https://{domain}/{obj_type}/{obj_token}"

                        # 如果有子节点，创建子目录并导出
                        if has_child:
                            # 创建以文档名命名的子目录
                            doc_dir = current_path / safe_title
                            doc_dir.mkdir(parents=True, exist_ok=True)

                            # 导出文档到子目录
                            file_path = exporter.export(
                                url=url,
                                output_dir=doc_dir,
                                filename=safe_title,
                                silent=True,
                            )
                            exported_count += 1
                            console.print(f"[green]✓ 已导出:[/green] {safe_title} → {doc_dir.relative_to(output)}")

                            # 递归处理子节点
                            traverse_nodes(node_token, depth + 1, doc_dir)
                        else:
                            # 无子节点，直接导出到当前目录
                            file_path = exporter.export(
                                url=url,
                                output_dir=current_path,
                                filename=safe_title,
                                silent=True,
                            )
                            exported_count += 1
                            console.print(f"[green]✓ 已导出:[/green] {safe_title}")
                    except Exception as e:
                        failed_count += 1
                        console.print(f"[red]✗ 导出失败:[/red] {safe_title} - {e}")
                else:
                    # 非文档类型（如文件夹），只递归处理子节点
                    if has_child:
                        # 为文件夹创建子目录
                        folder_dir = current_path / safe_title
                        folder_dir.mkdir(parents=True, exist_ok=True)
                        console.print(f"[cyan]📁 文件夹:[/cyan] {safe_title}")
                        traverse_nodes(node_token, depth + 1, folder_dir)

        # 开始遍历
        traverse_nodes(parent_node)

        # 输出统计
        console.print(Panel(
            f"✅ 导出完成!\n\n"
            f"[green]成功:[/green] {exported_count} 个文档\n"
            f"[red]失败:[/red] {failed_count} 个文档\n"
            f"[blue]输出目录:[/blue] {output}",
            border_style="green",
        ))

    except Exception as e:
        console.print(f"[red]❌ 批量导出失败: {e}[/red]")
        raise typer.Exit(1)


# ==============================================================================
# auth 命令
# ==============================================================================
@app.command()
def auth(
        app_id: Optional[str] = typer.Option(
            None,
            "--app-id",
            help="飞书应用 App ID（覆盖配置文件）",
        ),
        app_secret: Optional[str] = typer.Option(
            None,
            "--app-secret",
            help="飞书应用 App Secret（覆盖配置文件）",
        ),
        lark: bool = typer.Option(
            False,
            "--lark",
            help="使用 Lark (海外版)",
        ),
):
    """
    [yellow]❁[/] 获取授权，获取并缓存 Token

    首次使用前运行此命令进行授权：

        # 使用已配置的凭证（推荐，需先运行 feishu-docx config set）
        feishu-docx auth

        # 或指定凭证
        feishu-docx auth --app-id xxx --app-secret xxx

    授权成功后，Token 将被缓存，后续导出无需再次授权。
    """
    try:
        # 获取凭证
        final_app_id, final_app_secret = get_credentials(app_id, app_secret)

        if not final_app_id or not final_app_secret:
            console.print(
                "[red]❌ 需要提供 OAuth 凭证[/red]\n\n"
                "方式一：先配置凭证（推荐）\n"
                "  [cyan]feishu-docx config set --app-id xxx --app-secret xxx[/cyan]\n\n"
                "方式二：命令行传入\n"
                "  [cyan]feishu-docx auth --app-id xxx --app-secret xxx[/cyan]"
            )
            raise typer.Exit(1)

        authenticator = OAuth2Authenticator(
            app_id=final_app_id,
            app_secret=final_app_secret,
            is_lark=lark,
        )

        console.print("[yellow]>[/yellow] 正在进行 OAuth 授权...")
        token = authenticator.authenticate()

        console.print(Panel(
            f"✅ 授权成功！\n\n"
            f"Token 已缓存至: [cyan]{authenticator.cache_file}[/cyan]\n\n"
            f"后续使用 [green]feishu-docx export[/green] 命令将自动使用缓存的 Token。",
            title="授权成功",
            border_style="green",
        ))

    except Exception as e:
        console.print(f"[red]❌ 授权失败: {e}[/red]")
        raise typer.Exit(1)


# ==============================================================================
# tui 命令
# ==============================================================================
@app.command()
def tui():
    """
    [magenta]✪[/] TUI 交互界面

    提供终端图形界面进行文档导出操作。
    """
    try:
        from feishu_docx.tui.app import FeishuDocxApp
        app_tui = FeishuDocxApp()
        app_tui.run()
    except ImportError as e:
        console.print(f"[red]❌ TUI 模块加载失败: {e}[/red]")
        console.print("[yellow]请确保已安装 textual: pip install textual[/yellow]")
        raise typer.Exit(1)


# ==============================================================================
# config 命令组
# ==============================================================================
config_app = typer.Typer(help="[dim]❄[/] 配置管理", rich_markup_mode="rich")
app.add_typer(config_app, name="config")


@config_app.command("set")
def config_set(
        app_id: Optional[str] = typer.Option(
            None,
            "--app-id",
            help="飞书应用 App ID",
        ),
        app_secret: Optional[str] = typer.Option(
            None,
            "--app-secret",
            help="飞书应用 App Secret",
        ),
        lark: bool = typer.Option(
            False,
            "--lark",
            help="使用 Lark (海外版)",
        ),
):
    """
    设置飞书应用凭证

    配置后，export 和 auth 命令将自动使用这些凭证，无需每次传入。

    示例:
        feishu-docx config set --app-id cli_xxx --app-secret xxx
    """
    config = AppConfig.load()

    # 更新配置（只更新传入的值）
    if app_id:
        config.app_id = app_id
    if app_secret:
        config.app_secret = app_secret
    if lark:
        config.is_lark = lark

    # 交互式输入缺失的值
    if not config.app_id:
        config.app_id = typer.prompt("App ID")
    if not config.app_secret:
        config.app_secret = typer.prompt("App Secret", hide_input=True)

    config.save()

    console.print(Panel(
        f"✅ 配置已保存至: [cyan]{config.config_file}[/cyan]\n\n"
        f"App ID: [green]{config.app_id[:10]}...{config.app_id[-4:]}[/green]\n"
        f"App Secret: [dim]已保存（已隐藏）[/dim]\n"
        f"Lark 模式: {'是' if config.is_lark else '否'}\n\n"
        "现在你可以直接运行：\n"
        "  [cyan]feishu-docx auth[/cyan] - 进行 OAuth 授权\n"
        "  [cyan]feishu-docx export URL[/cyan] - 导出文档",
        title="配置成功",
        border_style="green",
    ))


@config_app.command("show")
def config_show():
    """显示当前配置"""
    config = AppConfig.load()

    table = Table(title="当前配置")
    table.add_column("配置项", style="cyan")
    table.add_column("来源", style="dim")
    table.add_column("值", style="green")

    # App ID
    app_id_env = os.getenv("FEISHU_APP_ID")
    if app_id_env:
        table.add_row("App ID", "环境变量",
                      f"{app_id_env[:10]}...{app_id_env[-4:]}" if len(app_id_env) > 14 else app_id_env)
    elif config.app_id:
        table.add_row("App ID", "配置文件",
                      f"{config.app_id[:10]}...{config.app_id[-4:]}" if len(config.app_id) > 14 else config.app_id)
    else:
        table.add_row("App ID", "-", "[dim]未设置[/dim]")

    # App Secret
    app_secret_env = os.getenv("FEISHU_APP_SECRET")
    if app_secret_env:
        table.add_row("App Secret", "环境变量", "[dim]已设置（已隐藏）[/dim]")
    elif config.app_secret:
        table.add_row("App Secret", "配置文件", "[dim]已设置（已隐藏）[/dim]")
    else:
        table.add_row("App Secret", "-", "[dim]未设置[/dim]")

    # Access Token
    if os.getenv("FEISHU_ACCESS_TOKEN"):
        table.add_row("Access Token", "环境变量", "[dim]已设置（已隐藏）[/dim]")
    else:
        if not (app_secret_env or config.app_secret) and not (app_id_env or config.app_id):
            table.add_row("Access Token", "-", "[dim]未设置[/dim]")

    # Lark 模式
    table.add_row("Lark 模式", "配置文件", "是" if config.is_lark else "否")

    # 缓存位置
    cache_dir = get_config_dir()
    table.add_row("配置文件", "-", "存在" if config.config_file.exists() else "❌ 不存在")
    table.add_row("Token 缓存", "-", "存在" if (cache_dir / "token.json").exists() else "❌ 不存在")
    table.add_row("配置目录", "-", str(cache_dir))

    console.print(table)

    # 提示
    if not config.has_credentials() and not app_id_env:
        console.print("\n[yellow]💡 提示: 运行以下命令配置凭证[/yellow]")
        console.print("   [cyan]feishu-docx config set --app-id xxx --app-secret xxx[/cyan]")


@config_app.command("clear")
def config_clear(
        force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
        token: bool = typer.Option(True, "--token", "-t", help="清除 Token 缓存"),
        config: bool = typer.Option(False, "--config", "-c", help="清除配置文件"),
        all: bool = typer.Option(False, "--all", "-a", help="同时清除配置和 Token 缓存"),
):
    """清除配置和缓存"""
    app_config = AppConfig.load()
    cache_dir = get_config_dir()
    token_file = cache_dir / "token.json"

    has_config = app_config.config_file.exists()
    has_token = token_file.exists()

    if not has_config and not has_token:
        console.print("[yellow]没有可清除的配置或缓存[/yellow]")
        return

    # 确认
    if not force:
        if all or (config and token):
            msg = "确定要清除配置文件和 Token 缓存吗？"
        elif config:
            msg = "确定要清除配置文件吗？（Token 缓存保留，使用 --all 同时清除配置）"
        else:
            msg = "确定要清除 Token 缓存吗？（配置文件保留，使用 --all 同时清除配置）"
        confirm = typer.confirm(msg)
        if not confirm:
            console.print("已取消")
            raise typer.Abort()

    # 清除
    if (all or config) and has_config:
        app_config.clear()
        console.print("[green]✅ 配置文件已清除[/green]")

    if (token or all) and has_token:
        token_file.unlink()
        console.print("[green]✅ Token 缓存已清除[/green]")


# ==============================================================================
# 入口点
# ==============================================================================
if __name__ == "__main__":
    app()
