# Clash 配置自动更新工具

一个基于 Flask 的 Web 应用，用于自动获取、过滤和管理 Clash 代理节点，支持链式代理配置。

## 功能特点

- 🔍 **智能节点获取**：从多个订阅 URL 自动获取代理节点
- 🌍 **地区过滤**：支持按地区（香港、台湾、美国、新加坡）过滤节点
- 🔗 **链式代理**：支持配置需要通过其他节点中转的特殊节点
- 📝 **灵活配置**：支持手动添加 Clash 格式节点，支持从 URL 批量导入
- 💾 **配置持久化**：保存和加载配置，方便下次使用
- 🔄 **Gist 集成**：自动上传配置到 GitHub Gist，支持订阅链接重用
- 📚 **多 Gist 管理**：支持管理多个命名的 Gist 配置，轻松切换不同场景
- 🔑 **Token 管理**：独立的 GitHub Token 配置界面，支持查看、修改和安全存储
- 🎨 **现代化界面**：响应式设计，操作直观

## 快速开始

### 1. 环境要求

- Python 3.7+
- GitHub 账号（用于上传 Gist）

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/sczheng189/clash-config-updater.git
cd clash-config-updater

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

#### 获取 GitHub Token

1. 访问 [GitHub Personal Access Tokens](https://github.com/settings/tokens)
2. 点击 "Generate new token" → "Generate new token (classic)"
3. 填写 Note（如 "Clash Config Updater"）
4. 勾选 `gist` 权限
5. 点击 "Generate token" 并复制生成的 token

#### 配置环境变量（可选）

创建 `.env` 文件（可参考 `.env.example`）：

```env
# 是否重用 Gist（保持订阅链接不变）
REUSE_GIST=true

# 默认使用的 Gist 名称（可选）
# 如果配置了多个 Gist，可以指定默认使用哪个
DEFAULT_GIST_NAME=生产环境
```

**注意**：GitHub Token 现在通过独立的 Web 界面管理，支持保存到 .env 文件或浏览器本地存储。

### 4. 运行

确保虚拟环境已激活，然后运行：

```bash
# Windows 用户可以使用批处理脚本
run.bat

# 或者直接运行
python app.py
```

访问 `http://localhost:5000` 即可使用。

## 使用说明

### 基本流程

1. **配置 GitHub Token**（首次使用）：
   - 在主界面的"GitHub Token 配置"区域点击"配置 Token"
   - 输入 GitHub Token，选择保存方式（.env 文件或本地存储）
   - 点击保存，配置状态会实时显示
2. **添加订阅链接**：在"订阅链接"区域粘贴订阅 URL
3. **选择地区过滤**：选择需要的节点地区（默认香港）
4. **获取节点**：点击"获取节点"按钮
5. **选择节点**：在节点列表中选择需要的节点
6. **选择上传方式**：
   - 勾选"重用 Gist"：选择要更新的现有 Gist
   - 不勾选：输入新 Gist 名称（可选，留空自动命名）
7. **配置链式代理**（可选）：为特殊节点设置 dialer-proxy
8. **生成配置**：点击"生成配置"
9. **复制订阅链接**：生成成功后复制订阅链接到 Clash

### 链式代理功能

适用于需要通过其他节点中转的特殊节点：

1. 在"添加需要链式代理的节点"区域添加特殊节点
2. 这些节点会自动标记为需要链式代理
3. 可以为每个节点单独设置 dialer-proxy 目标

### 配置管理

- **保存配置**：保存当前所有节点和设置
- **加载配置**：恢复之前保存的配置
- **清除配置**：删除所有保存的数据

### GitHub Token 管理

提供完善的 Token 管理功能：

#### Token 配置界面
1. **状态显示**：实时显示 Token 配置状态和掩码信息
2. **配置 Token**：安全输入和保存 GitHub Token
3. **查看 Token**：查看完整 Token 内容（仅限本地存储）
4. **修改 Token**：重新配置或更新现有 Token
5. **存储选择**：
   - **.env 文件**：永久保存，重启应用后仍有效（推荐）
   - **本地存储**：保存在浏览器中，仅当前浏览器可用

#### 安全特性
- Token 显示时使用掩码保护隐私
- 输入时支持密码显示切换
- 支持选择安全的存储方式

### 多 Gist 管理

支持管理多个命名的 Gist，适用于不同使用场景：

#### Gist 管理对话框功能
1. **添加已有 Gist**：输入名称和 Gist ID，将现有 Gist 添加到管理列表
2. **重命名 Gist**：修改 Gist 的显示名称
3. **删除 Gist**：移除不需要的 Gist（至少保留一个）

#### 使用方式
- **更新现有 Gist**：勾选"重用 Gist"，从下拉框选择要更新的 Gist
- **创建新 Gist**：不勾选"重用 Gist"，可输入自定义名称或使用自动命名
- **默认 Gist**：通过环境变量 `DEFAULT_GIST_NAME` 设置默认使用的 Gist

**使用场景示例**：
- 生产环境：稳定的节点配置
- 测试环境：用于测试的节点配置
- 备用配置：应急使用的节点配置

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

1. **GitHub Token**：需要有 `gist` 权限，通过独立的 Web 界面管理，可选择保存到 .env 文件或浏览器本地存储
2. **敏感信息**：`.env` 文件和 `.gist_id` 不会被提交到仓库
3. **数据目录**：`data/` 目录下的 JSON 文件包含用户配置，不会被提交
4. **Gist 配置**：`.gist_id` 文件支持多个 Gist，格式为 `名称:gist_id`，每行一个
5. **自动命名**：创建新 Gist 时，如果不指定名称，将使用格式 `Clash配置_YYYYMMDD_HHMMSS`
6. **Token 安全**：建议将 Token 保存到 .env 文件以确保重启后仍有效，本地存储仅限当前浏览器

## 更新日志

### v2.2.0 - GitHub Token 管理重构
- 重构：将 GitHub Token 配置独立为主界面专门区域
- 新增：Token 状态实时显示（配置状态、掩码显示）
- 新增：Token 查看和修改功能
- 新增：Token 存储方式选择（.env 文件或本地存储）
- 新增：Token 输入时的密码可见性切换
- 新增：Token 状态 API 端点 `/api/github-token`
- 改进：从 Gist 管理对话框中移除 Token 配置，简化界面
- 优化：Token 管理界面更加直观和安全

### v2.1.0 - 界面优化和 Token 管理改进
- 优化：GitHub Token 从主界面移至 Gist 管理对话框
- 新增：在 Gist 管理对话框中添加已有 Gist 功能
- 改进：简化主界面，根据"重用 Gist"选项动态显示相关内容
- 优化：Token 保存在浏览器本地存储，无需每次输入

### v2.0.0 - 多 Gist 管理功能
- 新增：支持管理多个命名的 Gist 配置
- 新增：Gist 管理界面（添加、重命名、删除）
- 新增：环境变量 `DEFAULT_GIST_NAME` 支持设置默认 Gist
- 改进：自动将旧格式 `.gist_id` 文件转换为新格式
- 修复：pip 镜像源 403 错误，更换为阿里云镜像源

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License