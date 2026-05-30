```markdown
# EggSearch 🥚🔍

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个现代化的 **Pterodactyl Game Egg 搜索工具**，帮助用户快速查找和筛选游戏服务器 Egg 配置。

在线体验：**[egg-search-gamma.vercel.app](https://egg-search-gamma.vercel.app)**

---

## ✨ 项目特性

- 🔍 **智能搜索**：支持关键词模糊搜索游戏 Egg
- 📋 **Egg 信息展示**：包含名称、作者、支持版本、描述等
- ⚡ **轻量高效**：基于 Python 开发，响应迅速
- 🌐 **API 支持**：可作为后端服务提供给前端或其它工具使用
- 🚀 **Vercel 部署**：已支持服务器less部署

---

## 🛠 技术栈

- **语言**：Python
- **框架**：FastAPI / Flask / Streamlit（根据 `main.py` 实现）
- **部署**：Vercel

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/caozuohua/EggSearch.git
cd EggSearch
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行项目

```bash
python main.py
```

或使用 uvicorn（如果使用 FastAPI）：

```bash
uvicorn main:app --reload
```

---

## 📁 项目结构

```
EggSearch/
├── main.py              # 主程序入口
├── requirements.txt     # 项目依赖
├── README.md
└── (其他配置文件)
```

---

## 📖 使用说明

1. 启动服务后访问对应地址
2. 在搜索框输入游戏名称（如 `minecraft`、`factorio`、`ark` 等）
3. 浏览搜索结果，查看详细 Egg 信息
4. 支持一键复制或导出配置（后续可扩展）

---

## 🤝 如何贡献

欢迎大家一起完善 Egg 数据库和搜索功能！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/xxx`)
3. 提交修改 (`git commit -m 'Add some feature'`)
4. 推送分支 (`git push origin feature/xxx`)
5. 提交 Pull Request

---

## 📄 开源协议

本项目采用 **MIT License** 开源协议。

---

## ⭐ 支持一下

如果你觉得这个项目有用，欢迎 **Star** 支持作者继续维护！

**Made with ❤️ by zuohua**

---

---

**提交建议**：

1. 把上面的内容**覆盖**现有的 `README.md`
2. 如果你有项目截图，可以在 `screenshots/` 文件夹中添加，然后在 README 里引用
3. 补充 `LICENSE` 文件（MIT）

