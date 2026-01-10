# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：__init__.py
# @Date   ：2025/01/09 18:30
# @Author ：leemysw
# 2025/01/09 18:30   Create
# =====================================================
"""
[INPUT]: None
[OUTPUT]: 对外提供版本号 __version__ 和主要 API
[POS]: feishu_docx 包入口，是整个项目的对外接口
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

__version__ = "0.1.1"

from feishu_docx.core.exporter import FeishuExporter

__all__ = ["__version__", "FeishuExporter"]
