# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- 改进获取文档块列表的逻辑以支持分页获取所有blocks
- 使用官方的Block模型
- 新增 larkoffice.com 域名文件解析(部分文档图片无权限下载)
- 支持 Markdown 本地转换与图片回填，创建时可上传完整文档

## [0.1.4] - 2026-01-16

### Added
- 文件/附件 Block 支持，生成带临时下载链接的 markdown（📎 格式）

---

## [0.1.3] - 2026-01-12

### Added
- CLI `--stdout` / `-c` 参数，直接输出内容到标准输出（适合 AI Agent）
- TUI Access Token 输入框支持
- TUI URL 输入历史（上下箭头浏览）
- TUI 动态进度回调，实时显示解析进度
- TUI 详细错误日志（显示 traceback 最后 3 行）
- OAuth 授权页面简约重新设计（深色主题）
- GitHub Actions 自动发布到 PyPI

### Changed
- README 图片链接改为 GitHub raw 链接（PyPI 可显示）
- OAuth 页面模板抽取到 `auth/templates.py`

### Fixed
- README 中英文切换链接修复

---

## [0.1.0] - 2026-01-10

### Added
- 初始版本发布
- 云文档 (docx) 导出为 Markdown
- 电子表格 (sheet) 导出为 Markdown 表格
- 多维表格 (bitable) 导出为 Markdown 表格
- 知识库 (wiki) 节点自动解析导出
- 图片自动下载并本地引用
- 画板导出为图片
- OAuth 2.0 授权 + Token 自动刷新
- CLI 命令行工具
- TUI 终端界面（基于 Textual）
- Claude Skills 支持
