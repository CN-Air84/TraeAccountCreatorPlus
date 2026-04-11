# TraeAccountCreatorPlus

基于 Playwright + 临时邮箱的 Trae 账号批量注册工具，支持单账号注册与批量并发注册。

## ✨ 特性

- 🎯 单账号注册与批量并发注册
- 📧 集成 Temporam 临时邮箱服务
- 💾 自动保存账号信息和 Cookie
- 🌐 现代化 Web 界面（可选）
- 🚀 独立 EXE 可执行文件

## 📦 安装与使用

### 方式一：使用 EXE（推荐）

1. 下载 `dist/TraeAccountCreator.exe`
2. 双击运行
3. 在浏览器中访问 http://localhost:8080
4. 配置 API Key 并开始注册

### 方式二：Python 源码运行

#### 环境要求

- Python 3.13+
- Playwright 浏览器

#### 安装依赖

```bash
pip install -r requirements.txt
python -m playwright install
```

#### 运行

**命令行模式：**
```bash
python register.py [注册数量] [并发数] [检查CD]
```

**GUI 模式：**
```bash
python gui.py
```

**Web 模式：**
```bash
python server.py
```
然后访问 http://localhost:8080

## ⚙️ 配置

### 获取 API Key

1. 访问 https://temporam.com/zh/dashboard
2. 注册/登录账号
3. 在控制台中创建 API Key
4. 将 API Key 填入 `mail_client.py` 第 4 行

### 使用参数

- **注册数量**：要注册的账号数量
- **并发数**：同时运行的注册任务数（建议 1-10）
- **检查 CD**：邮件检查间隔秒数（建议 8-15 秒）

## 📁 输出文件

- `accounts.txt` - 账号密码列表
- `cookies/` - Cookie 文件目录
- `sessions/` - Session 存储目录

## 🔧 常见问题

### 收不到验证码邮件

- 检查 API Key 是否正确
- 尝试增加检查 CD 时间
- 修改 `mail_client.py` 中的域名筛选条件

### 注册失败

- 检查网络连接（需能访问 Google）
- 确认 API 配额充足
- 降低并发数

### API 配额不足

Temporam 每个账号提供 1000 次免费额度，额度用完后需要：
- 更换 API Key
- 或等待下个月重置

## ⚠️ 免责声明

本工具仅供学习和技术研究使用：

- ⚠️ **风险自负**：使用者需自行承担所有风险
- ⚖️ **法律风险**：可能违反软件使用协议
- 🚫 **责任豁免**：作者不承担任何损失责任
- 📚 **使用限制**：仅限个人学习研究，严禁商业用途
- 🔒 **授权声明**：不得用于绕过软件正当授权机制

使用前请务必阅读完整的免责声明。

## 💡 技术栈

- **后端**: Python 3.13, aiohttp, Playwright
- **前端**: 原生 HTML/CSS/JavaScript
- **临时邮箱**: Temporam API
- **打包工具**: PyInstaller

## 📄 项目结构

```
.
├── register.py          # 核心注册逻辑
├── mail_client.py       # 临时邮箱客户端
├── gui.py              # Tkinter GUI 界面
├── server.py           # Web 服务器
├── index.html          # Web 界面
├── build_exe.py        # EXE 打包脚本
└── dist/
    ├── TraeAccountCreator.exe  # 可执行文件
    ├── 使用说明.md
    └── 启动程序.bat
```

## 🙏 项目来源

本项目基于以下项目修改而来：

- [Trae-Account-Creator](https://github.com/S-Trespassing/Trae-Account-Creator)
- [TraeAccountRegister](https://github.com/kggzs/TraeAccountRegister)

## 📝 更新日志

### v2.0
- ✅ 添加 Web 界面
- ✅ 打包为独立 EXE
- ✅ 优化 UI 设计
- ✅ 改进错误处理

### v1.0
- ✅ 基于 Temporam 临时邮箱
- ✅ 支持批量并发注册
- ✅ 自动保存账号信息
