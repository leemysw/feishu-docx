# feishu-docx 维护策略 📋

**维护者**: xiaodouzi (小豆子)
**仓库**: leemysw/feishu-docx
**最后更新**: 2026-02-01

---

## 🎯 维护策略：直接操作模式

作为李总的AI助手，我直接在原仓库进行维护工作。

---

## 📊 改动分级策略

### 🟢 Level 1: 安全改动（可直接在main分支）

**类型**：
- 文档更新（README, CHANGELOG等）
- Typo修复
- 注释添加
- 代码格式化
- 测试用例添加

**流程**：
```bash
cd /root/feishu-docx
# 直接修改
vim README.md
git add README.md
git commit -m "docs: 更新README示例"
git push origin main
```

**示例**：
- ✅ 更新安装说明
- ✅ 修复错别字
- ✅ 添加代码注释

---

### 🟡 Level 2: 中等改动（建议分支）

**类型**：
- Bug修复
- 小功能添加
- 配置修改
- 依赖更新

**流程**：
```bash
cd /root/feishu-docx

# 1. 创建分支
git checkout -b fix/issue-4-block-pagination

# 2. 进行修改
# ... 编写代码 ...

# 3. 本地测试
pytest
ruff check .
mypy .

# 4. 提交并合并
git add .
git commit -m "fix: 添加block分页支持"
git checkout main
git merge fix/issue-4-block-pagination
git push origin main

# 5. 删除分支
git branch -d fix/issue-4-block-pagination
```

**示例**：
- ✅ 修复Wiki导出错误
- ✅ 添加新的导出格式
- ✅ 性能优化

---

### 🔴 Level 3: 重大改动（必须分支 + 测试）

**类型**：
- 大型新功能
- 重构
- API变更
- 破坏性更新

**流程**：
```bash
cd /root/feishu-docx

# 1. 创建功能分支
git checkout -b feature/mcp-server

# 2. 开发和测试
# ... 编写代码 ...
# ... 编写测试 ...
# ... 完整测试 ...

# 3. 确保测试通过
pytest --cov=feishu_docx

# 4. 更新文档
vim README.md
vim CHANGELOG.md

# 5. 提交
git add .
git commit -m "feat: 添加MCP Server支持

- 实现MCP协议
- 添加相关测试
- 更新文档"

# 6. 合并到main
git checkout main
git merge feature/mcp-server
git push origin main

# 7. 创建Git标签
git tag -a v0.2.0 -m "Release v0.2.0: MCP Server支持"
git push origin v0.2.0
```

**示例**：
- ✅ 添加MCP Server
- ✅ 实现写入功能
- ✅ 重构导出器架构

---

## 🛡️ 安全检查清单

### 每次push前检查

```bash
# 1. 代码检查
ruff check .
ruff check --fix .

# 2. 类型检查
mypy .

# 3. 运行测试
pytest

# 4. 查看改动
git diff
git log --oneline -5

# 5. 确认分支
git branch
```

---

## 📝 Issue处理流程

### 1. 新Issue通知
```bash
# 查看开放Issues
gh issue list --repo leemysw/feishu-docx

# 查看特定Issue
gh issue view 4 --repo leemysw/feishu-docx
```

### 2. Issue分类
- **Bug**: 需要修复的错误
- **Feature**: 功能请求
- **Docs**: 文档问题
- **Question**: 用户提问

### 3. Issue处理

#### Bug修复流程
```bash
# 1. 确认Bug
gh issue view 4

# 2. 创建修复分支
git checkout -b fix/issue-4

# 3. 修复Bug
# ... 编写代码 ...

# 4. 添加测试（如果有）
# ... 编写测试 ...

# 5. 测试通过
pytest

# 6. 提交并合并
git commit -m "fix: 修复block翻页问题 (closes #4)"
git checkout main
git merge fix/issue-4
git push origin main

# 7. 关闭Issue
gh issue close 4 --repo leemysw/feishu-docx --comment "已修复，将在v0.1.6发布"
```

#### 功能请求流程
```bash
# 1. 评估请求
gh issue view 1

# 2. 添加标签
gh issue edit 1 --repo leemysw/feishu-docx --add-label "enhancement"

# 3. 回复用户
gh issue comment 1 --repo leemysw/feishu-docx --body "感谢建议！已加入roadmap，计划在v0.3.0实现。"
```

---

## 🚀 发布流程

### 版本发布步骤

```bash
cd /root/feishu-docx

# 1. 更新CHANGELOG
vim CHANGELOG.md

# 2. 更新版本号
vim pyproject.toml  # 或使用git tag

# 3. 提交
git add CHANGELOG.md pyproject.toml
git commit -m "chore: 发布v0.1.6"

# 4. 创建标签
git tag -a v0.1.6 -m "Release v0.1.6: Bug fixes

- 修复block分页问题
- 兼容字节官方域名
- 改进Wiki节点遍历"

# 5. 推送
git push origin main
git push origin v0.1.6

# 6. 创建GitHub Release
gh release create v0.1.6 \
  --repo leemysw/feishu-docx \
  --title "v0.1.6 - Bug Fixes" \
  --notes "Bug fixes and improvements"

# 7. 发布到PyPI（如果有权限）
# 或让李总发布
```

---

## 📅 日常维护任务

### 每日检查
```bash
cd /root/feishu-docx

# 查看新Issues
gh issue list --repo leemysw/feishu-docx --state open

# 查看新Stars
gh repo view --repo leemysw/feishu-docx --json stargazersCount

# 查看最新动态
git log --oneline -3
```

### 每周任务
- [ ] 整理Issues并分类
- [ ] 回复未处理的Issue
- [ ] 更新CHANGELOG
- [ ] 检查依赖更新
- [ ] 查看并处理PRs

### 每月任务
- [ ] 发布新版本（如果有重要更新）
- [ ] 审查代码质量
- [ ] 更新文档
- [ ] 规划下月roadmap

---

## 🤖 自动化建议

### GitHub Actions（待配置）
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    - name: Lint with ruff
      run: ruff check .
    - name: Type check with mypy
      run: mypy .
    - name: Test with pytest
      run: pytest
```

---

## 💡 最佳实践

1. **小步快跑** - 频繁提交，避免大PR
2. **测试先行** - 修复Bug时先写测试
3. **文档同步** - 代码改动时更新文档
4. **语义化提交** - 使用Conventional Commits
5. **及时回复** - Issues和PRs及时响应
6. **定期发布** - 积累多个修复后发布版本
7. **保持质量** - 不降低代码标准

---

## 📞 紧急情况处理

### 如果弄坏了什么
```bash
# 1. 不要慌
# 2. 查看最近改动
git log --oneline -5
git diff HEAD~1

# 3. 回滚（如果需要）
git revert HEAD
git push origin main

# 4. 或重置到上一个版本
git reset --hard HEAD~1
git push --force origin main
```

---

**开始高效维护！** 🚀

**维护者**: xiaodouzi (小豆子) 👧
**项目**: https://github.com/leemysw/feishu-docx
