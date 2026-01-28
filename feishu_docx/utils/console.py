# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：console.py
# @Date   ：2026/01/28 12:25
# @Author ：leemysw
# 2026/01/28 10:55   Create
# 2026/01/28 12:05   Improve fallback printing
# 2026/01/28 12:25   Configure stdio for GBK consoles
# =====================================================
"""
[INPUT]: 依赖 rich.console 的 Console
[OUTPUT]: 对外提供 SafeConsole 和 get_console
[POS]: utils 模块的控制台输出封装
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import sys
from typing import Any

from rich.console import Console


def _configure_stdio() -> None:
    """
    为非 UTF-8 控制台配置安全输出

    Windows 上常见的 GBK/CP936 编码在输出 emoji/特殊符号时会抛 UnicodeEncodeError，
    将 stdout/stderr 的 errors 设为 replace，避免 CLI 因输出崩溃。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            continue


_configure_stdio()


def _is_utf8_encoding(encoding: str | None) -> bool:
    if not encoding:
        return False
    return encoding.lower().replace("-", "") == "utf8"


def _sanitize_text(text: str, encoding: str) -> str:
    try:
        text.encode(encoding)
        return text
    except Exception:
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


class SafeConsole(Console):
    """
    Unicode 安全的 Console

    避免在 GBK 等非 UTF-8 环境输出 emoji/特殊字符时崩溃。
    """

    def print(self, *objects: Any, **kwargs: Any) -> None:  # type: ignore[override]
        try:
            return super().print(*objects, **kwargs)
        except UnicodeEncodeError:
            encoding = self.encoding or sys.stdout.encoding or "utf-8"
            sanitized = []
            for obj in objects:
                if isinstance(obj, str):
                    sanitized.append(_sanitize_text(obj, encoding))
                else:
                    sanitized.append(_sanitize_text(str(obj), encoding))
            fallback_kwargs = dict(kwargs)
            fallback_kwargs.setdefault("markup", False)
            return super().print(*sanitized, **fallback_kwargs)


def get_console() -> SafeConsole:
    """
    返回兼容控制台输出的 Console 实例
    """
    encoding = sys.stdout.encoding or ""
    if _is_utf8_encoding(encoding):
        return SafeConsole()
    return SafeConsole(emoji=False, safe_box=True)
