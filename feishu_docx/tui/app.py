# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：app.py
# @Date   ：2025/01/09 18:30
# @Author ：leemysw
# 2025/01/09 18:30   Create
# =====================================================
"""
[INPUT]: 依赖 textual 的 TUI 框架，依赖 feishu_docx.core.exporter 导出器
[OUTPUT]: 对外提供 FeishuDocxApp 类
[POS]: tui 模块的主应用
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import warnings

warnings.filterwarnings("ignore", category=UserWarning)

import os
from datetime import datetime

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Input, Static, RichLog, ProgressBar

from feishu_docx.core.exporter import FeishuExporter
from feishu_docx.utils.config import AppConfig

from .constants import LOGO, DESCRIPTION, VERSION, AUTHOR, REPO
from .styles import APP_CSS


# ==============================================================================
# 主应用
# ==============================================================================
class FeishuDocxApp(App):
    """飞书文档导出器 TUI"""

    CSS = APP_CSS

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit", show=False),
        Binding("enter", "export", "Export"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+z", "undo", "Undo", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.config = AppConfig.load()
        self.exporting = False
        self._input_history: dict[str, list[str]] = {}
        # URL 历史
        self._url_history: list[str] = []
        self._url_history_index: int = -1

    def compose(self) -> ComposeResult:
        # 认证状态
        has_token = bool(os.getenv("FEISHU_ACCESS_TOKEN"))
        has_creds = self.config.has_credentials() or (
                os.getenv("FEISHU_APP_ID") and os.getenv("FEISHU_APP_SECRET")
        )

        if has_token:
            auth_text, auth_class = "● Token 已配置", "status-ok"
        elif has_creds:
            auth_text, auth_class = "● OAuth 已配置", "status-ok"
        else:
            auth_text, auth_class = "○ 未配置凭证", "status-warn"

        # ───────── 顶部 ─────────
        with Vertical(id="header"):
            yield Static(LOGO, id="logo")
            yield Static(DESCRIPTION, id="desc-line")
            yield Static(f"{VERSION} · by {AUTHOR} · {REPO}", id="info-line")

        # ───────── 主内容 ─────────
        with Horizontal(id="content"):
            # 左侧：配置面板
            with Vertical(id="left-panel"):
                yield Static("─ Config ─", classes="panel-title")
                yield Static("")

                with Horizontal(classes="field-row"):
                    yield Static("URL", classes="field-label")
                    yield Static(">> ", classes="field-prompt")
                    yield Input(placeholder="(输入飞书文档URL)", id="url-input", classes="field-input")

                with Horizontal(classes="field-row"):
                    yield Static("Output", classes="field-label")
                    yield Static(">> ", classes="field-prompt")
                    yield Input(value="./output", id="output-input", classes="field-input")

                with Horizontal(classes="field-row"):
                    yield Static("TBL FMT", classes="field-label")
                    yield Static(">> ", classes="field-prompt")
                    yield Input(value="md", id="table-type-input", classes="field-input")

                yield Static("")
                yield Static("─ Auth ─", classes="panel-title")

                with Horizontal(classes="field-row"):
                    yield Static("Status", classes="field-label")
                    yield Static("   ", classes="field-prompt")
                    yield Static(auth_text, id="auth-status", classes=auth_class)

                with Horizontal(classes="field-row"):
                    yield Static("Token", classes="field-label")
                    yield Static(">> ", classes="field-prompt")
                    yield Input(
                        value=os.getenv("FEISHU_ACCESS_TOKEN", "") or "",
                        id="token-input",
                        classes="field-input",
                        password=True,
                        placeholder="(Access Token, 优先使用)",
                    )

                with Horizontal(classes="field-row"):
                    yield Static("App ID", classes="field-label")
                    yield Static(">> ", classes="field-prompt")
                    yield Input(
                        value=os.getenv("FEISHU_APP_ID", "") or self.config.app_id or "",
                        id="app-id-input",
                        classes="field-input",
                        placeholder="(App ID)",
                    )

                with Horizontal(classes="field-row"):
                    yield Static("Secret", classes="field-label")
                    yield Static(">> ", classes="field-prompt")
                    yield Input(
                        value=os.getenv("FEISHU_APP_SECRET", "") or self.config.app_secret or "",
                        id="app-secret-input",
                        classes="field-input",
                        password=True,
                        placeholder="(App Secret)",
                    )

                # 进度区
                with Vertical(id="progress-section"):
                    yield Static("Ready", id="progress-text")
                    yield ProgressBar(total=100, show_eta=False, id="progress-bar")

            # 右侧：日志面板
            with Vertical(id="right-panel"):
                yield Static("─ Logs ─", classes="panel-title")
                yield RichLog(id="log-view", auto_scroll=True, markup=True, highlight=True, wrap=True)

        yield Footer()

    # ==========================================================================
    # 生命周期
    # ==========================================================================
    def on_mount(self):
        """挂载时初始化"""
        self.write_log("Welcome to feishu-docx!")
        self.write_log("Input URL and press [bold cyan]Enter[/] to export")

        if self.config.has_credentials():
            self.write_log("[dim]Credentials loaded from config[/dim]")

    # ==========================================================================
    # 辅助方法
    # ==========================================================================
    def write_log(self, msg: str):
        """写日志"""
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#log-view", RichLog).write(f"[dim]{ts}[/] {msg}")

    def set_progress(self, value: int, text: str):
        """设置进度"""
        self.query_one("#progress-bar", ProgressBar).update(progress=value)
        self.query_one("#progress-text", Static).update(text)

    # ==========================================================================
    # Actions
    # ==========================================================================
    def action_clear(self):
        """清空日志"""
        self.query_one("#log-view", RichLog).clear()
        self.write_log("Log cleared")

    def action_save(self):
        """保存配置"""
        try:
            self.config.app_id = self.query_one("#app-id-input", Input).value.strip()
            self.config.app_secret = self.query_one("#app-secret-input", Input).value.strip()
            self.config.save()
            self.write_log("[green]✓ Config saved[/]")

            status = self.query_one("#auth-status", Static)
            status.update("● OAuth 已配置")
            status.remove_class("status-warn")
            status.add_class("status-ok")
        except Exception as e:
            self.write_log(f"[red]✗ Save failed: {e}[/]")

    def action_undo(self):
        """撤回上一次输入"""
        focused = self.focused
        if isinstance(focused, Input) and focused.id:
            history = self._input_history.get(focused.id, [])
            if len(history) > 1:
                history.pop()
                prev_value = history[-1] if history else ""
                focused.value = prev_value
                self.write_log("[dim]Undo[/]")

    def action_export(self):
        """执行导出"""
        if self.exporting:
            return
        self.run_export()

    # ==========================================================================
    # 事件处理
    # ==========================================================================
    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed):
        """记录输入变化，用于撤回"""
        input_id = event.input.id
        if input_id:
            if input_id not in self._input_history:
                self._input_history[input_id] = []
            history = self._input_history[input_id]
            if len(history) >= 10:
                history.pop(0)
            history.append(event.value)

    @on(Input.Submitted, "#url-input")
    def on_url_enter(self, event: Input.Submitted):
        """URL 输入回车触发导出"""
        # 保存到历史
        url = event.value.strip()
        if url and (not self._url_history or self._url_history[-1] != url):
            self._url_history.append(url)
            self._url_history_index = len(self._url_history)
        self.action_export()

    def on_key(self, event) -> None:
        """处理上下键浏览 URL 历史"""
        url_input = self.query_one("#url-input", Input)
        if not url_input.has_focus:
            return

        if event.key == "up" and self._url_history:
            event.prevent_default()
            if self._url_history_index > 0:
                self._url_history_index -= 1
                url_input.value = self._url_history[self._url_history_index]
        elif event.key == "down" and self._url_history:
            event.prevent_default()
            if self._url_history_index < len(self._url_history) - 1:
                self._url_history_index += 1
                url_input.value = self._url_history[self._url_history_index]
            else:
                self._url_history_index = len(self._url_history)
                url_input.value = ""

    # ==========================================================================
    # 后台任务
    # ==========================================================================
    @work(thread=True)
    def run_export(self):
        """后台执行导出"""
        self.exporting = True

        url = self.query_one("#url-input", Input).value.strip()
        output_dir = self.query_one("#output-input", Input).value.strip()
        table_format = self.query_one("#table-type-input", Input).value.strip()

        if not url:
            self.call_from_thread(self.write_log, "[red]✗ URL is required[/]")
            self.exporting = False
            return

        self.call_from_thread(self.set_progress, 5, "连接中...")
        self.call_from_thread(self.write_log, f"[cyan]>[/] {url[:50]}...")

        # 进度回调
        def on_progress(stage: str, current: int, total: int):
            if total > 0:
                pct = int((current / total) * 80) + 10  # 10-90% 范围
            else:
                pct = 10
            self.call_from_thread(self.set_progress, pct, stage)
            if current == 0 or current == total:
                self.call_from_thread(self.write_log, f"[dim]  {stage}[/]")

        try:
            # 优先使用 Token
            token = self.query_one("#token-input", Input).value.strip() or os.getenv("FEISHU_ACCESS_TOKEN")

            if token:
                exporter = FeishuExporter.from_token(token)
            else:
                app_id = self.query_one("#app-id-input", Input).value.strip() or self.config.app_id
                app_secret = self.query_one("#app-secret-input", Input).value.strip() or self.config.app_secret

                if not app_id or not app_secret:
                    self.call_from_thread(self.write_log, "[red]✗ No credentials configured[/]")
                    self.call_from_thread(self.set_progress, 0, "Ready")
                    self.exporting = False
                    return

                exporter = FeishuExporter(app_id=app_id, app_secret=app_secret)

            output_path = exporter.export(
                url=url,
                output_dir=output_dir,
                table_format=table_format,
                silent=True,
                progress_callback=on_progress,
            )

            self.call_from_thread(self.set_progress, 100, "Done!")
            self.call_from_thread(self.write_log, f"[green]✓ {output_path}[/]")

        except Exception as e:
            self.call_from_thread(self.set_progress, 0, "Error")
            # 详细错误信息
            import traceback
            error_msg = str(e)
            self.call_from_thread(self.write_log, f"[red]✗ {error_msg}[/]")
            # 如果有详细堆栈，显示最后几行
            tb = traceback.format_exc()
            for line in tb.strip().split('\n')[-3:]:
                if line.strip():
                    self.call_from_thread(self.write_log, f"[dim]{line}[/]")
        finally:
            self.exporting = False


# ==============================================================================
# 入口点
# ==============================================================================
if __name__ == "__main__":
    app = FeishuDocxApp()
    app.run()
