# feishu-docx GitHub Issues 任务清单 📝

**更新时间**: 2026-02-01
**维护者**: xiaodouzi (小豆子)

---

## 🔴 开放Issues概览

当前有 **3个开放Issues** 需要关注：

### Issue #9: Wiki无法导出 ⚠️
**用户**: KevinFan1
**创建时间**: 2026-01-29
**标签**: 无
** reactions**: 👍 1

**问题描述**:
- 直接调用`.export`方法飞书报错 "not found"
- 缺少知识库节点的遍历
- 用户已经自己魔改实现了解决方案

**用户提供的代码**:
```python
def walk_nodes(*, space_id: str, token: str, parent_node_token: str = "", base_path: str = "./output"):
    """递归遍历 wiki 节点"""
    # 完整实现见Issue详情
```

**优先级**: 🔴 高
**状态**: 需要评估并集成用户方案

---

### Issue #4: 兼容block翻页和字节官方文档 🐛
**用户**: Gahyu96
**创建时间**: 2026-01-27
**评论数**: 3

**问题描述**:
1. **超过500的block没有翻页** - 导出的文档不全
2. **需要兼容字节官方域名** - `bytedance.larkoffice.com`
3. **多种格式内容获取失败** - API报错

**错误信息**:
```
API 调用失败: wiki.v2.space.get_node
  code: 131005
  msg: not found

API 调用失败: sheets.v3.spreadsheet.get
  code: 1310214
  msg: Path param :spreadsheet_token is not exist
```

**优先级**: 🔴 高
**状态**: Bug修复

---

### Issue #1: 询问下进度 💬
**用户**: 2488583886
**创建时间**: 2026-01-14
**评论数**: 1

**问题描述**:
- 用户询问read/write/update功能的实现时间
- 期待MCP支持
- 想把飞书当做真正的知识库使用

**优先级**: 🟡 中
**状态**: 功能请求，需要回复

---

## 📋 行动计划

### 立即行动（今天）
1. **回复Issue #1** - 说明roadmap和时间表
2. **评估Issue #9** - 检查用户提供的解决方案
3. **分析Issue #4** - 定位block翻页和域名兼容问题

### 本周任务
- [ ] 修复Issue #4的block翻页问题
- [ ] 添加字节官方域名支持
- [ ] 集成Issue #9的Wiki遍历方案
- [ ] 更CHANGELOG.md

### 下周任务
- [ ] 发布修复版本 v0.1.6
- [ ] 添加更多测试用例
- [ ] 更新文档和示例

---

## 🔧 技术分析

### Issue #4 - Block翻页问题
**根本原因**: 飞书API单次最多返回500个block，超过的需要分页获取

**解决方案**:
```python
# 需要添加分页逻辑
def fetch_all_blocks(doc_token: str, token: str) -> List[Block]:
    blocks = []
    page_token = ""
    while True:
        response = api.get_blocks(doc_token, token, page_token)
        blocks.extend(response.items)
        if not response.has_more:
            break
        page_token = response.page_token
    return blocks
```

### Issue #9 - Wiki节点遍历
**用户方案**: 递归遍历Wiki节点树
- 有子节点 → 创建目录并递归
- 无子节点 → 导出文档

**集成策略**: 将用户方案集成到`export-wiki-space`命令

### Issue #1 - 功能请求
**需要回复的内容**:
- 感谢用户认可
- 说明当前优先级是Bug修复
- 写入功能计划在v0.3.0
- MCP支持已在roadmap

---

## 📝 回复草稿

### 回复 Issue #1
```markdown
感谢您的认可和反馈！🎉

关于read/write/update功能：
- 当前优先级：修复现有Bug和稳定性问题
- 写入功能：计划在v0.3.0实现（预计1-2个月）
- MCP支持：已在roadmap，会尽快推进
- 知识库CRUD：这是我们的最终目标

欢迎贡献代码和测试！🙏
```

### 回复 Issue #9
```markdown
感谢你的反馈和代码分享！👍

你的Wiki遍历方案很好，我会：
1. 评估集成到主代码
2. 优化并添加错误处理
3. 在下一个版本发布

@KevinFan1 如果有兴趣提交PR，欢迎贡献！
```

### 回复 Issue #4
```markdown
收到！这些问题确实存在，我会：
1. 添加block分页支持
2. 兼容字节官方域名
3. 修复API调用错误

预计本周发布修复版本v0.1.6 🚀
```

---

## 🎯 版本规划

### v0.1.6 (Bug修复)
- [ ] 修复block翻页问题
- [ ] 兼容字节官方域名
- [ ] 改进Wiki节点遍历
- [ ] 修复API调用错误

### v0.2.0 (功能增强)
- [ ] MCP Server支持
- [ ] 导出格式扩展
- [ ] 性能优化

### v0.3.0 (写入功能)
- [ ] 创建文档
- [ ] 更新文档
- [ ] 删除文档
- [ ] 完整CRUD

---

**下次更新**: 完成Issue修复后
