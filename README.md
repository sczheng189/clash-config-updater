# Clash 配置自动更新工具

一个基于 Flask 的 Web 应用，用于自动获取、过滤和管理 Clash 代理节点，支持链式代理配置。

## 功能特点

- 🔍 **智能节点获取**：从多个订阅 URL 自动获取代理节点
- 🌍 **地区过滤**：支持按地区（香港、台湾、美国、新加坡）过滤节点
- 🔗 **链式代理**：支持配置需要通过其他节点中转的特殊节点
- 📝 **灵活配置**：支持手动添加 Clash 格式节点，支持从 URL 批量导入
- 💾 **配置持久化**：保存和加载配置，方便下次使用
- 🔄 **Gist 集成**：自动上传配置到 GitHub Gist，支持订阅链接重用
- 🎨 **现代化界面**：响应式设计，操作直观

## 快速开始

### 1. 环境要求

- Python 3.7+
- GitHub 账号（用于上传 Gist）

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/clash-config-updater.git
cd clash-config-updater

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

创建 `.env` 文件（可参考 `.env.example`）：

```env
# GitHub Token（可选，也可在界面中输入）
GITHUB_TOKEN=your_github_token_here

# 是否重用 Gist（保持订阅链接不变）
REUSE_GIST=true
```

### 4. 运行

Windows 用户：
```bash
run.bat
```

其他系统：
```bash
python app.py
```

访问 `http://localhost:5000` 即可使用。

## 使用说明

### 基本流程

1. **添加订阅链接**：在"订阅链接"区域粘贴订阅 URL
2. **选择地区过滤**：选择需要的节点地区（默认香港）
3. **获取节点**：点击"获取节点"按钮
4. **选择节点**：在节点列表中选择需要的节点
5. **配置链式代理**（可选）：为特殊节点设置 dialer-proxy
6. **生成配置**：输入 GitHub Token，点击"生成配置"
7. **复制订阅链接**：生成成功后复制订阅链接到 Clash

### 链式代理功能

适用于需要通过其他节点中转的特殊节点：

1. 在"添加需要链式代理的节点"区域添加特殊节点
2. 这些节点会自动标记为需要链式代理
3. 可以为每个节点单独设置 dialer-proxy 目标

### 配置管理

- **保存配置**：保存当前所有节点和设置
- **加载配置**：恢复之前保存的配置
- **清除配置**：删除所有保存的数据

## 项目结构

```
├── app.py                  # Flask 应用主文件
├── utils.py               # 配置管理核心类
├── subscription_parser.py  # 订阅解析器
├── templates/
│   └── index.html         # 前端页面
├── static/
│   ├── css/
│   │   └── style.css      # 样式文件
│   └── js/
│       └── main.js        # 前端逻辑
├── data/                  # 数据存储目录
│   ├── urls.json          # URL 历史记录
│   └── chained_proxy_config.json  # 链式代理配置
├── example.yaml           # Clash 配置模板
├── requirements.txt       # Python 依赖
├── .env.example          # 环境变量示例
├── .gitignore            # Git 忽略文件
└── run.bat               # Windows 启动脚本
```

## 注意事项

1. **GitHub Token**：需要有 `gist` 权限
2. **敏感信息**：`.env` 文件和 `.gist_id` 不会被提交到仓库
3. **数据目录**：`data/` 目录下的 JSON 文件包含用户配置，不会被提交

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License