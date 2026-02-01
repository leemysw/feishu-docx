# feishu-docx 项目维护说明 📚

**项目**: https://github.com/xiaotangdou/feishu-docx (fork)
**上游仓库**: https://github.com/leemysw/feishu-docx
**维护者**: xiaodouzi (小豆子)
**本地路径**: /root/feishu-docx

---

## 🎯 工作流程

### 日常维护工作流

```bash
cd /root/feishu-docx

# 1. 同步上游最新代码
git fetch upstream
git rebase upstream/main

# 2. 创建功能分支
git checkout -b feature/fix-issue-4

# 3. 进行修改和测试
# ... 编写代码 ...

# 4. 提交更改
git add .
git commit -m "feat: 修复block翻页问题"

# 5. 推送到自己的fork
git push origin feature/fix-issue-4

# 6. 创建Pull Request到上游仓库
# 通过GitHub网页或gh cli创建PR
```

---

## 📂 项目结构

```
/root/feishu-docx/
├── feishu_docx/          # 核心代码
│   ├── cli/              # CLI命令
│   ├── exporter/         # 导出器
│   └── api/              # API接口
├── .skills/              # Claude Skills
├── docs/                 # 文档
├── tests/                # 测试
├── MAINTENANCE.md        # 维护计划
├── ISSUES_TODO.md        # Issue任务清单
├── pyproject.toml        # 项目配置
└── README.md             # 项目说明
```

---

## 🔧 Git仓库配置

### 远程仓库
- **origin**: https://github.com/xiaotangdou/feishu-docx.git (我的fork)
- **upstream**: https://github.com/leemysw/feishu-docx.git (原始仓库)

### 常用命令

```bash
# 查看远程仓库
git remote -v

# 同步上游代码
git fetch upstream
git merge upstream/main
# 或使用rebase保持线性历史
git rebase upstream/main

# 推送到我的fork
git push origin main

# 创建分支
git checkout -b feature/branch-name

# 切换分支
git checkout main

# 查看状态
git status

# 查看日志
git log --oneline -10
```

---

## 🎯 当前任务清单

### 🔴 高优先级
1. **Issue #4**: 修复block翻页和字节域名兼容
2. **Issue #9**: 集成Wiki节点遍历功能

### 🟡 中优先级
1. **Issue #1**: 回复功能请求，说明roadmap
2. 更新文档和示例
3. 添加更多测试用例

### 🟢 低优先级
1. 代码优化和重构
2. 性能优化
3. 新功能开发

---

## 📝 开发规范

### 提交信息规范
```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具链相关
- `perf`: 性能优化

**示例**:
```bash
git commit -m "feat: 添加block分页支持"
git commit -m "fix: 修复Wiki导出not found错误"
git commit -m "docs: 更新README使用示例"
```

### 分支命名规范
- `feature/xxx` - 新功能
- `fix/xxx` - Bug修复
- `hotfix/xxx` - 紧急修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 重构

---

## 🧪 测试

### 运行测试
```bash
cd /root/feishu-docx

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_exporter.py

# 查看覆盖率
pytest --cov=feishu_docx
```

### 代码检查
```bash
# 代码格式检查
ruff check .

# 自动修复
ruff check --fix .

# 类型检查
mypy .
```

---

## 🚀 发布流程

### 发布新版本
```bash
# 1. 更新版本号（在pyproject.toml或git tag）
git tag -a v0.1.6 -m "Release v0.1.6: Bug fixes"

# 2. 推送tag
git push origin v0.1.6

# 3. 创建GitHub Release（通过gh cli）
gh release create v0.1.6 --notes "Bug fixes and improvements"

# 4. 发布到PyPI（如果有权限）
# 或通过PR让原仓库作者发布
```

---

## 📊 项目统计

**上游仓库 (leemysw/feishu-docx)**:
- ⭐ Stars: 40
- 🍴 Forks: 5
- 🐛 Open Issues: 3
- 📦 Language: Python
- 🔧 License: MIT

**我的fork (xiaotangdou/feishu-docx)**:
- ✅ 维护文档已添加
- 🔧 准备开始维护

---

## 💡 提示

1. **定期同步upstream** - 保持代码最新
2. **小步快跑** - 频繁提交，避免大PR
3. **测试先行** - 修复Bug时先写测试
4. **文档同步** - 代码改动时更新文档
5. **沟通优先** - 重大改动前先讨论

---

**开始维护吧！** 🚀

**维护者**: xiaodouzi (小豆子) 👧
**最后更新**: 2026-02-01
