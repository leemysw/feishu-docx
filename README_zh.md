<div align="center">

<img src="https://raw.githubusercontent.com/leemysw/feishu-docx/main/docs/icon.png" alt="feishu-docx" width="128">

# feishu-docx

<p align="center">
  <em>飞书知识库导出、写入与云空间管理工具 | 支持 Markdown、公众号导入、CLI、TUI、OAuth 2.0</em>
</p>

[![PyPI version](https://badge.fury.io/py/feishu-docx.svg)](https://badge.fury.io/py/feishu-docx)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<p align="center">
  <strong>中文</strong> | <a href="https://github.com/leemysw/feishu-docx/blob/main/README.md">English</a>
</p>
</div>

<div align="center">
<img src="https://raw.githubusercontent.com/leemysw/feishu-docx/main/docs/tui.png" alt="feishu-docx TUI" width="90%">
</div>

---

## 🆕 最近重要更新（v0.2.8）

- 修复 PDF 表格换行和粗体、斜体、删除线与行内代码组合的渲染问题，其他原始 HTML 继续安全转义（[#37](https://github.com/leemysw/feishu-docx/issues/37)）
- 卡片视图链接保留标题和目标地址，正确处理 URL 编码
- 更新项目图标，并新增公开文档 Markdown / PDF 端到端回归测试

需要 PDF 导出时，使用 `pip install --upgrade "feishu-docx[pdf]"` 升级；已通过 uv tool 安装的用户可运行 `uv tool upgrade feishu-docx`。

---

## 🎯 为什么选择 feishu-docx？

**让 AI Agent 读懂、写入并管理你的飞书知识库。**

- 🤖 **为AI而生** — 完美支持 Claude/GPT Skills，让 Agent 直接查询飞书文档
- 📄 **全面覆盖** — 云文档、电子表格、多维表格、知识库、公众号文章
- ✍️ **支持写回** — 创建文档、追加内容、更新指定 Block
- ☁️ **云空间管理** — 列文件、删文件、权限管理、批量清空
- 🔐 **自动授权** — 一次授权，Token 自动刷新，告别手动管理
- 🎨 **双重界面** — CLI 命令行 + TUI 终端图形界面，任君选择
- 📦 **安装简单** — `uv tool install feishu-docx` 或 `pip install feishu-docx`

---

## ⚡ 30秒快速开始

### 安装

推荐使用 `uv tool install`（隔离环境，不污染系统 Python）：

```bash
uv tool install feishu-docx
```

可选功能依赖单独安装，核心包保持轻量：

```bash
# PDF 导出：--pdf、--pdf-template、--pdf-logo、代码高亮
uv tool install 'feishu-docx[pdf]'

# 浏览器导出：export-browser
uv tool install 'feishu-docx[browser]'
playwright install chromium
```

也可以不安装直接运行：

```bash
uvx feishu-docx export "https://my.feishu.cn/wiki/xxx"
```

如果还没有安装 `uv`：`curl -LsSf https://astral.sh/uv/install.sh | sh`

备选：`pip install`（适合虚拟环境，或显式使用 `--break-system-packages`）：

```bash
pip install feishu-docx
```

可选依赖也可以用 `pip` 安装：

```bash
pip install 'feishu-docx[pdf]'
pip install 'feishu-docx[browser]'
playwright install chromium
```

> 在 zsh 等 shell 中请保留引号，例如 `'feishu-docx[pdf]'`，否则 `[]` 可能会被当成 glob 匹配。

> ⚠️ 在虚拟环境外直接 `pip install`，可能会在现代 Linux/macOS 上遇到 `externally-managed-environment`（PEP 668）。推荐使用虚拟环境或 `uv tool install`。

### 配置并导出

```bash
# 配置凭证（只需一次）
feishu-docx config set --app-id YOUR_APP_ID --app-secret YOUR_APP_SECRET

# 导出！（自动获取 tenant_access_token，无需 OAuth 授权）
feishu-docx export "https://my.feishu.cn/wiki/KUIJwaBuGiwaSIkkKJ6cfVY8nSg"

# 直接从公众号抓取并创建飞书文档
feishu-docx create --url "https://mp.weixin.qq.com/s/xxxxx"

# 管理应用云空间中的文档
feishu-docx drive ls --type docx

# 可选：使用 OAuth 模式获取用户级权限
# feishu-docx config set --auth-mode oauth && feishu-docx auth
```

---

## 🤖 Skills 支持

**让 Agent 直接访问你的飞书知识库！**

本项目已包含 Claude Skills 配置，位于 `.skills/feishu-docx/SKILL.md`。
支持 OpenCode、Claude Code、Codex、Cursor 等 Agent / IDE 环境。

将此 Skill 复制到你的 Agent 项目中，Claude 就能：

- 📖 读取飞书知识库作为上下文
- 🔍 搜索和引用内部文档
- 📝 创建文档、追加内容、更新指定 Block

---

## ✨ 功能特性

| 功能                  | 描述                         |
|---------------------|----------------------------|
| 📄 云文档导出            | Docx → Markdown，保留格式、图片、表格 |
| 📊 电子表格导出           | Sheet → Markdown 表格，支持富文本单元格与公式/计算值模式 |
| 📋 多维表格导出           | Bitable → Markdown 表格      |
| 📚 知识库导出            | Wiki 节点自动解析，支持嵌套结构         |
| 🗂️ Wiki 批量导出       | 递归导出整个知识空间，保持目录层级结构        |
| ✍️ 文档写入             | 创建文档、追加 Markdown、更新指定 Block |
| 📰 公众号导入导出          | 公众号文章导出 Markdown / 直接导入飞书 |
| 🌐 Browser-based 导出 | 导出公开文档或浏览器会话可读文档，并下载本地资源 |
| ☁️ 云空间管理            | 列文件、删文件、公开权限、成员权限、批量清空 |
| 🗄️ 数据库结构导出         | APaaS 数据库表结构导出为 Markdown   |
| 🧷 本地资源下载           | 图片和附件保存到本地，Markdown 相对路径引用    |
| 🖨️ PDF 导出            | 使用 WeasyPrint 生成品牌化 PDF，支持自定义 CSS 模板 |
| 🔐 认证方式             | 自动 tenant_access_token（推荐）/ OAuth 2.0 |
| 🎨 精美 TUI           | 基于 Textual 的终端图形界面         |

### ✅ 支持的Block

本工具目前支持导出以下飞书/ Lark 文档组件：

| 组件分类     | 具体内容                     | 支持情况 | 备注            |
|:---------|:-------------------------|:----:|:--------------|
| **基础文本** | 标题、正文、列表、任务(Todo)、代码块、引用 |  ✅   | 完美支持          |
| **文本样式** | 加粗、斜体、删除线、下划线、链接、@人员     |  ✅   | 完美支持          |
| **布局结构** | 分栏、高亮块、分割线               |  ✅   | 完美支持          |
| **表格**   | 原生表格                     |  ✅   | 支持导出为 md/html |
| **多媒体**  | 图片、画板                    |  ✅   | 画板将导出为图片      |
| **嵌入文档** | 电子表格、多维表格                |  ✅   | Sheet 支持富文本单元格与公式/计算值模式 |
| **特殊块**  | 同步块、Add-ons Block         |  ✅  | 同步块支持同文档与跨文档引用展开 |
| **文件**   | 附件                       |  ✅   | 优先本地下载，失败时回退临时链接    |

---

## 📖 使用方式

### 适用场景

- 导出飞书文档、Sheet、Bitable、Wiki 为 Markdown
- 抓取微信公众号文章并导出为 Markdown
- 抓取微信公众号文章并直接创建飞书文档
- 创建/追加/更新飞书文档内容
- 管理应用云空间或个人云空间中的文件和权限

### CLI 命令行

`export-browser` 依赖 Playwright：

如果使用 `uv tool install` 安装，请安装 browser extra：

```bash
uv tool install 'feishu-docx[browser]'
playwright install chromium
```

如果在虚拟环境中使用：

```bash
pip install 'feishu-docx[browser]'
playwright install chromium
```

```bash
# 导出单个文档到指定目录
feishu-docx export "https://xxx.feishu.cn/docx/xxx" -o ./docs

# 控制 Sheet 导出为计算值或公式（仅影响 Sheet 与嵌入 Sheet）
feishu-docx export "https://xxx.feishu.cn/wiki/xxx" --table md --sheet-value-mode display
feishu-docx export "https://xxx.feishu.cn/wiki/xxx" --table md --sheet-value-mode formula

# 在真实浏览器会话中导出公开文档或当前浏览器可读文档
feishu-docx export-browser "https://xxx.larkoffice.com/wiki/xxx" -o ./browser_docs

# 复用已有 Playwright 登录态导出
feishu-docx export-browser "https://xxx.larkoffice.com/wiki/xxx" --storage-state ./storage_state.json

# 批量导出整个知识空间（保持层级结构）
feishu-docx export-wiki-space <space_id_or_url> -o ./wiki_backup --max-depth 5

# 导出 APaaS 数据库结构
feishu-docx export-workspace-schema <workspace_id> -o ./database_schema.md

# 导出公众号文章为 Markdown
feishu-docx export-wechat "https://mp.weixin.qq.com/s/xxxxxx"

# 导出为 PDF（需安装 pdf extra）
uv tool install 'feishu-docx[pdf]'  # 或: pip install 'feishu-docx[pdf]'
feishu-docx export "https://xxx.feishu.cn/docx/xxx" --pdf

# 使用自定义品牌 CSS 模板导出 PDF
feishu-docx export "https://xxx.feishu.cn/docx/xxx" --pdf --pdf-template ./brand.css

# 封面页添加 Logo
feishu-docx export "https://xxx.feishu.cn/docx/xxx" --pdf --pdf-template ./brand.css --pdf-logo ./logo.svg

# 使用代码高亮主题
feishu-docx export "https://xxx.feishu.cn/docx/xxx" --pdf --syntax-style solarized-light

# 抓取公众号文章并创建飞书文档
feishu-docx create --url "https://mp.weixin.qq.com/s/xxxxxx"

# 在 tenant 模式下列出应用云空间中的文档
feishu-docx drive ls --type docx

# 查看和修改文档公开权限
feishu-docx drive perm-show "https://xxx.feishu.cn/docx/xxx"
feishu-docx drive perm-set "https://xxx.feishu.cn/docx/xxx" --share-entity anyone_can_view

# 双重确认后清空云空间文件
feishu-docx drive clear --type docx

# 使用 Token（临时）
feishu-docx export "URL" -t your_access_token

# 启动 TUI 界面
feishu-docx tui
```

### Python API

```python
from feishu_docx import FeishuExporter

# 初始化（使用 tenant_access_token，推荐）
exporter = FeishuExporter(app_id="xxx", app_secret="xxx")

# 导出单个文档
path = exporter.export("https://xxx.feishu.cn/wiki/xxx", "./output")

# 获取文档内容（不保存文件）
content = exporter.export_content("https://xxx.feishu.cn/docx/xxx")

# 导出为 PDF（需执行: uv tool install 'feishu-docx[pdf]' 或 pip install 'feishu-docx[pdf]'）
path = exporter.export("https://xxx.feishu.cn/docx/xxx", "./output", pdf=True)

# 使用自定义品牌 CSS 模板导出 PDF
from pathlib import Path
path = exporter.export(
    "https://xxx.feishu.cn/docx/xxx",
    "./output",
    pdf=True,
    pdf_template=Path("./brand.css"),
    pdf_logo=Path("./logo.svg"),
    syntax_style="solarized-light",  # 可选 Pygments 代码高亮主题
)

# 在真实浏览器会话中导出公开文档或当前浏览器可读文档
browser_path = exporter.export_with_browser(
    "https://xxx.larkoffice.com/wiki/xxx",
    "./browser_output",
)

# 获取使用浏览器导出的 Markdown 内容（不保存文件）
browser_content = exporter.export_content_with_browser(
    "https://xxx.larkoffice.com/wiki/xxx",
)

# 批量导出整个知识空间
result = exporter.export_wiki_space(
    space_id="xxx",
    output_dir="./wiki_backup",
    max_depth=3,
)
print(f"导出 {result['exported']} 个文档到 {result['space_dir']}")
```

---

## 🔐 配置飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/) 创建应用
2. 添加重定向 URL：`http://127.0.0.1:9527/`
3. 申请以下权限：

```python
"docx:document:readonly"  # 查看云文档
"wiki:wiki:readonly"  # 查看知识库
"drive:drive:readonly"  # 查看云空间文件（图片下载）
"sheets:spreadsheet:readonly"  # 查看电子表格
"bitable:app:readonly"  # 查看多维表格
"board:whiteboard:node:read"  # 查看白板
"contact:contact.base:readonly"  # 获取用户基本信息（@用户名称）
"offline_access"  # 离线访问（获取 refresh_token）
```

4. 保存凭证：

```bash
feishu-docx config set --app-id cli_xxx --app-secret xxx
```

### 🔑 认证模式

| | **Tenant 模式** (默认) | **OAuth 模式** |
|---|---|---|
| **Token 类型** | `tenant_access_token` | `user_access_token` |
| **配置方式** | 在[开放平台](https://open.feishu.cn/app)预配置权限 | OAuth 流程中动态申请权限 |
| **用户操作** | ✅ 自动获取，无需用户操作 | ❌ 需要在浏览器中授权 |
| **访问范围** | **应用**有权限的文档 | **用户**有权限的文档 |
| **适用场景** | 服务端自动化、AI Agent | 访问用户私有文档 |

**Tenant 模式（推荐）：**
```bash
# 一次性配置
feishu-docx config set --app-id xxx --app-secret xxx

# 导出（自动获取 tenant_access_token）
feishu-docx export "https://xxx.feishu.cn/docx/xxx"
```

> ⚠️ Tenant 模式需要在[飞书开放平台](https://open.feishu.cn/app) → 应用权限中预先配置文档权限。

**云空间管理（tenant / oauth）：**
```bash
# tenant 模式：管理应用云空间
feishu-docx drive ls --type docx

# oauth 模式：管理个人云空间
feishu-docx drive ls --auth-mode oauth --type docx
```

> 📎 飞书会根据 access token 类型区分云空间：`tenant_access_token` 对应应用云空间，`user_access_token` 对应个人云空间。应用云空间资源无法直接通过 UI 管理，需要使用 Drive/File API 管理。

**OAuth 模式（访问用户文档）：**
```bash
# 一次性配置
feishu-docx config set --app-id xxx --app-secret xxx --auth-mode oauth
feishu-docx auth  # 在浏览器中完成授权

# 导出（使用缓存的 user_access_token）
feishu-docx export "https://xxx.feishu.cn/docx/xxx"
```

> 💡 OAuth 模式在授权时动态申请权限，无需预先配置。

---

## 📖 命令参考

| 命令                              | 描述                      |
|---------------------------------|-------------------------|
| `export <URL>`                  | 导出单个文档为 Markdown        |
| `export-browser <URL>`          | 在真实浏览器会话中导出公开 / 浏览器可读文档 |
| `export-wiki-space <space_id>`  | 批量导出知识空间（保持目录层级）        |
| `export-workspace-schema <id>`  | 导出 APaaS 数据库结构         |
| `export-wechat <URL>`           | 导出公众号文章为 Markdown       |
| `create <title>`                | 创建飞书文档（支持 --url 导入公众号） |
| `drive ls`                      | 列出应用云空间 / 个人云空间文件   |
| `drive rm <TOKEN>`              | 删除云空间文件                 |
| `drive perm-show <TOKEN>`       | 查看公开权限                  |
| `drive perm-set <TOKEN>`        | 更新公开权限                  |
| `drive perm-members <TOKEN>`    | 列出权限成员                  |
| `drive perm-add <TOKEN>`        | 新增权限成员                  |
| `drive perm-update <TOKEN>`     | 更新权限成员                  |
| `drive perm-rm <TOKEN>`         | 删除权限成员                  |
| `drive clear`                   | 双重确认后批量清空文件            |
| `write <URL>`                   | 向文档追加 Markdown 内容      |
| `update <URL>`                  | 更新文档中指定 Block          |
| `auth`                          | OAuth 授权                |
| `tui`                           | TUI 交互界面                |
| `config set`                    | 设置凭证                    |
| `config show`                   | 查看配置                    |
| `config clear`                  | 清除缓存                    |

## 📚 文档结构建议

- `README`：总览、快速开始、命令索引
- `docs/*.md`：复杂主题的专题文档

当前已提供：

- [云空间管理](./docs/drive-management.md)

---

## 🛠️ 开发

```bash
git clone https://github.com/leemysw/feishu-docx.git
cd feishu-docx
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 🗺️ Roadmap

- [x] 云文档/表格/知识库导出
- [x] OAuth 2.0 + Token 刷新
- [x] TUI 终端界面
- [x] Claude Skills 支持
- [x] 批量导出整个知识空间
- [x] 写入飞书（创建/更新文档）
- [x] 使用浏览器导出与本地资源下载

---

## 📜 更新日志

查看 [CHANGELOG.md](./CHANGELOG.md) 了解版本历史。

## 📚 更多文档

- [云空间管理](./docs/drive-management.md)

---

## 📄 开源协议

MIT License - 详见 [LICENSE](LICENSE)

---

**⭐ 如果这个项目对你有帮助，请给一个 Star！**
