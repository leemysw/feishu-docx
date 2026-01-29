# !/usr/bin/env python
# -*- coding: utf-8 -*-
# =====================================================
# @File   ：config.py
# @Date   ：2025/01/09 18:30
# @Author ：leemysw
# 2025/01/09 18:30   Create
# =====================================================
"""
[INPUT]: 依赖 pathlib 的路径操作，依赖 json 的序列化
[OUTPUT]: 对外提供 AppConfig 类和配置目录获取函数
[POS]: utils 模块的配置管理，支持持久化存储 app_id/app_secret
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ==============================================================================
# 路径工具函数
# ==============================================================================
def get_config_dir() -> Path:
    """获取配置目录 (~/.feishu-docx)"""
    config_dir = Path.home() / ".feishu-docx"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_cache_dir() -> Path:
    """获取缓存目录"""
    cache_dir = get_config_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


# ==============================================================================
# 应用配置
# ==============================================================================
@dataclass
class AppConfig:
    """
    应用配置
    
    存储路径: ~/.feishu-docx/config.json
    """
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    is_lark: bool = False

    # 配置文件路径
    _config_file: Path = None  # type: ignore

    def __post_init__(self):
        self._config_file = get_config_dir() / "config.json"

    @classmethod
    def load(cls) -> "AppConfig":
        """从配置文件加载配置"""
        config = cls()
        if config._config_file.exists():
            try:
                data = json.loads(config._config_file.read_text(encoding="utf-8"))
                config.app_id = data.get("app_id")
                config.app_secret = data.get("app_secret")
                config.is_lark = data.get("is_lark", False)
            except Exception:
                pass  # 配置文件损坏，使用默认值
        return config

    def save(self) -> None:
        """保存配置到文件"""
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
            "is_lark": self.is_lark,
        }
        self._config_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def clear(self) -> None:
        """清除配置"""
        self.app_id = None
        self.app_secret = None
        self.is_lark = False
        if self._config_file.exists():
            self._config_file.unlink()

    def has_credentials(self) -> bool:
        """检查是否已配置凭证"""
        return bool(self.app_id and self.app_secret)

    @property
    def config_file(self) -> Path:
        """配置文件路径"""
        return self._config_file
