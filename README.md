# 🔍 AI 搜索助手

一个具备多轮搜索能力的 AI 搜索原型产品，能够智能拆解关键词、自动验证结果质量、生成结构化研究报告。

## ✨ 功能特点

- 🧠 **智能关键词拆解**：将自然语言问题转换为搜索引擎关键词
- 🔄 **多轮搜索验证**：自动判断结果质量，不足时自动补充搜索
- 📝 **报告自动生成**：基于搜索结果生成结构化的研究报告
- 🎯 **结果质量筛选**：AI 验证搜索结果的相关性和质量

## 🛠️ 技术栈

- **后端**：Python + Flask
- **大模型**：DeepSeek API
- **搜索引擎**：Tavily Search API
- **前端**：原生 HTML + CSS + JavaScript

## 📦 安装运行

### 1. 克隆项目

```bash
git clone https://github.com/lindixu6-hash/search.git
cd search
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件，填入你的 API Key：

```bash
# DeepSeek API（申请地址：https://platform.deepseek.com）
DEEPSEEK_API_KEY=your_deepseek_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Tavily API（申请地址：https://tavily.com）
TAVILY_API_KEY=your_tavily_key_here
TAVILY_URL=https://api.tavily.com/search

# 服务端口
PORT=3000
```

### 4. 运行项目

```bash
python app.py
```

访问 `http://localhost:3000` 即可使用。

## 🎯 核心逻辑

```
用户输入问题
    ↓
AI 拆解关键词
    ↓
调用搜索引擎 API
    ↓
AI 验证结果质量
    ↓
结果不足？→ 是 → 扩充关键词 → 重新搜索
    ↓
   否
    ↓
合并所有搜索结果
    ↓
AI 生成研究报告
```

## 🚀 项目亮点

- **多轮搜索策略**：设计了三层判断机制（数量、上限、AI 质量判断）
- **轮次差异化**：第一轮和后续轮次的关键词生成策略不同
- **Token 管理**：控制上下文长度，每个结果只取摘要信息
- **错误处理**：API 调用失败时的降级处理

## 📝 待优化方向

- [ ] 搜索过程可视化
- [ ] 结果来源标注和跳转
- [ ] 报告导出功能（PDF/Word）
- [ ] 搜索历史记录
- [ ] 结果去重

## 📄 许可证

MIT License

---

**作者**：lindixu6-hash  
**项目时间**：2025年5月  
**项目状态**：✅ MVP 完成
