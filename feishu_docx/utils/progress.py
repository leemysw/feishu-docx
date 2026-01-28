# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：progress.py
# @Date   ：2026/01/28 12:05
# @Author ：leemysw
# 2025/01/10 21:50   Create
# 2026/01/28 12:05   Use safe console output
# =====================================================
"""
[INPUT]: 依赖 rich.progress 的进度显示组件
[OUTPUT]: 对外提供 ProgressManager 类
[POS]: utils 模块的进度管理器，供 parsers 使用
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from contextlib import contextmanager
from typing import Callable, Generator, Optional

from feishu_docx.utils.console import get_console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

ConsoleCallback = Callable[[str, int, int], None]
Advance = Callable[[], None]

console = get_console()


class ProgressManager:
    """
    统一的进度管理器
    
    支持两种模式：
    - CLI 模式：使用 Rich Progress 显示进度
    - TUI 模式：通过回调函数报告进度（silent=True）
    """

    def __init__(
        self,
        *,
        silent: bool = False,
        callback: Optional[ConsoleCallback] = None,
    ):
        self.silent = silent
        self.callback = callback

    # -------------------------------------------------------------------------
    # 基础能力
    # -------------------------------------------------------------------------

    def report(self, stage: str, current: int, total: int) -> None:
        """报告进度"""
        if self.callback:
            self.callback(stage, current, total)

    def log(self, message: str) -> None:
        """输出日志（仅非静默模式）"""
        if not self.silent:
            console.print(message)

    # -------------------------------------------------------------------------
    # Spinner
    # -------------------------------------------------------------------------

    @contextmanager
    def spinner(self, description: str):
        """Spinner 上下文管理器"""
        self.report(description, 0, 0)

        if self.silent:
            yield
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(f"[cyan]{description}[/cyan]", total=None)
            yield

    # -------------------------------------------------------------------------
    # Progress Bar
    # -------------------------------------------------------------------------

    @contextmanager
    def bar(self, description: str, total: int) -> Generator[Advance, None, None]:
        """进度条上下文管理器"""
        self.report(description, 0, total)
        current = 0

        if self.silent:

            def advance() -> None:
                nonlocal current
                current += 1
                self.report(description, current, total)

            yield advance
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=20),
            TaskProgressColumn(),
            transient=True,
        ) as progress:
            task_id = progress.add_task(f"[cyan]{description}[/cyan]", total=total)

            def advance() -> None:
                nonlocal current
                current += 1
                progress.advance(task_id, 1)
                self.report(description, current, total)

            yield advance
