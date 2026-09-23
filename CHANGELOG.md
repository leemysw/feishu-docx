# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- 重新设计项目图标，并用于中英文 README

### Fixed
- 修复 PDF 表格换行显示为字面量 `<br>` 的问题，其他原始 HTML 继续安全转义（#37）
- 修复粗体、斜体和删除线与行内代码组合时显示 Markdown 标记的问题（#37）

## [0.2.7] - 2026-07-08

### Added
- PDF 导出新增自定义 CSS 模板、封面 Logo 与可配置 Pygments 代码高亮主题支持
- 新增 `pdf` 与 `browser` 可选依赖，PDF / 浏览器导出相关包可按需安装

### Changed
- README、README_zh 与 Skill 安装说明补充 PDF / 浏览器导出的可选依赖安装方式

### Fixed
- 修复 PDF 封面标题直接拼接 HTML 的问题，标题内容会在渲染前转义

## [0.2.6] - 2026-05-14

### Added
- 合并社区贡献，新增 Add-ons Block 渲染支持

### Fixed
- 修复 Sheet 富文本单元格导出为 Python list/dict 字符串的问题

## [0.2.5] - 2026-04-11

### Fixed
- 修复 `export-wiki-space` 在公开知识空间首页 URL 下因 `items=None` 崩溃的问题，并修正首页 URL 的导出范围解析

## [0.2.4] - 2026-04-08

### Added
- `export` / `export-wiki-space` 新增 `--sheet-value-mode`，支持在导出 Sheet 时选择展示值或公式

### Fixed
- 修复 Sheet 导出默认保留公式文本的问题，改为优先导出单元格展示值

## [0.2.3] - 2026-03-30

### Added
- 新增 `export-browser` CLI，可在公开文档或提供浏览器会话状态的场景下直接导出 Markdown
- 新增 Browser-based 导出模块 `feishu_docx.core.browser_export`，按提取器、解析器、资源下载器、导出器拆分目录结构
- `FeishuExporter` 新增 `export_content_with_browser()` 与 `export_with_browser()` 方法

### Changed
- Browser-based 导出现在会同时下载图片、附件、白板和图表资源，并将 Markdown 链接替换为本地相对路径
- Browser-based 导出的文件名清洗逻辑会去除换行等空白字符，避免生成异常路径
- Browser-based 导出的资源目录结构与默认 `export` 对齐，统一保存到“文档同名目录”根下
- 公开文档图片的 SDK 降级下载会先访问文档 URL 预热匿名会话，再复用同一 HTTP 客户端请求 cover 资源
- 默认 `export` 的附件块在存在资源目录时会优先下载到本地，并复用同一匿名会话客户端

### Fixed
fix issue #22, 默认使用本地 Markdown 转换器

## [0.2.2] - 2026-03-11

### Added
- 新增 `drive` 命令组，支持在应用云空间或个人云空间中列出文件、删除文件、查看/更新公开权限、管理权限成员
- 新增 `DriveAPI` SDK 子模块，封装 `drive.v1.file` 与 `drive.v1.permission_*` 文件管理能力
- 新增云空间资源 URL / token 解析能力，支持从 `docx`、`sheet`、`bitable`、`wiki`、`folder` 等链接中提取 token
- 新增 `drive clear` 高风险清空命令，默认执行双重确认
- 新增专题文档 `docs/drive-management.md`

### Fixed
- 修复 Markdown 嵌套列表写入飞书时 `children` 结构不兼容的问题，改为递归创建子块
- 修复包含 YAML front matter 的 Markdown 文件写入异常，写入前会先清理 front matter
- 修复 Markdown 表格本地创建流程，按飞书限制自动拆分超过 9 行的表格并逐个回填单元格内容
- 修复 Block 创建请求体清洗逻辑，使用飞书 SDK `Block` 模型构造请求并移除不允许的响应字段
- 修复 `write` 命令中的调试断点残留

## [0.2.1] - 2026-03-02

### Added
- 新增 `create --url`：支持输入微信公众号文章 URL，自动抓取并创建飞书云文档
- 新增 `export-wechat` CLI 命令：支持输入微信公众号文章 URL，导出为 Markdown 文件
- 新增 `WeChatArticleImporter`：支持文章元数据提取、正文转 Markdown、图片下载与本地替换

## [0.2.0] - 2026-02-01

### 🚀 Major Refactoring

#### SDK 架构重构
- **组合模式重构** - SDK 从单体类拆分为 7 个职责清晰的子模块：
  - `sdk.docx` - 云文档操作
  - `sdk.sheet` - 电子表格操作
  - `sdk.bitable` - 多维表格操作
  - `sdk.wiki` - 知识库操作
  - `sdk.media` - 媒体资源操作
  - `sdk.contact` - 联系人操作
  - `sdk.apaas` - APaaS 数据库操作
- **懒加载机制** - 子模块按需初始化，提升启动性能
- **完全向后兼容** - 旧 API 保持可用

#### CLI 模块拆分
- **模块化重构** - 1110 行 `main.py` 拆分为 7 个独立模块：
  - `main.py` - 入口，命令注册
  - `common.py` - 共享工具函数
  - `cmd_export.py` - 导出命令
  - `cmd_write.py` - 写入命令
  - `cmd_apaas.py` - APaaS 命令
  - `cmd_auth.py` - 认证命令
  - `cmd_config.py` - 配置命令
  - `cmd_tui.py` - TUI 命令

### Added
- **知识空间批量导出 API** - `FeishuExporter.export_wiki_space()` 方法，支持 Python API 调用
- `WikiAPI.get_space_info()` - 获取知识空间名称
- 导出目录自动使用 space_name 命名子目录
- 所有 CLI 命令新增 `--auth-mode` 参数，支持命令行指定认证模式
- 新增环境变量 `FEISHU_AUTH_MODE` 支持
- `get_credentials()` 三参数独立优先级：命令行 > 环境变量 > 配置文件

### Changed
- 认证逻辑统一化，`app_id`、`app_secret`、`auth_mode` 遵循相同优先级规则
- Parser 使用组合模式 SDK，代码更简洁
- Wiki SDK 方法失败时抛出异常而不是返回 None

---

## [0.1.5] - 2026-01-29

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
