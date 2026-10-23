# Arc Forever — 让 Arc 浏览器在停服后继续使用（macOS 离线 / 免云端验证）

**在官方停服与账号下线后，继续在 macOS 上永久使用你的 Arc 浏览器——支持离线运行，完整保留所有 Spaces、置顶标签、扩展与个人配置。**

[English](README.md) · [兼容性说明](docs/compatibility.md) · [技术原理](docs/architecture.md)

## 核心特性

- **告别停服与强制退出**：接管本地身份验证，移除远程账号过期与强制下线限制，让 Arc 在停服后依然能正常启动和浏览。
- **完整保留工作流**：直接作用于现有的 `Arc.app`，你的 Spaces、收藏夹、历史记录、已安装扩展与个人配置原封不动。
- **原生体验，一键可逆**：自动备份原始文件，支持随时一键恢复至修改前状态，兼容标准 macOS 环境（Apple Silicon & Intel）。
- **侧边栏书签导出**：内置独立导出工具，无需启动浏览器即可将所有 Spaces 和置顶标签导出为标准 HTML 书签或 JSON。

## 快速开始

确保系统已安装 Python 3 与 Xcode Command Line Tools（终端运行 `xcode-select --install`），并在操作前退出 Arc。

### 方式一：双击交互运行（推荐）
下载仓库后，在 Finder 中双击打开 [`Arc Forever.command`](Arc%20Forever.command)，在终端菜单中按数字选择即可完成激活、状态检查或恢复。

### 方式二：命令行一键启用
```sh
git clone https://github.com/ChambersXDU/Arc-Forever.git
cd Arc-Forever

# 启用本地永久补丁
python3 arc_forever.py apply
```

完成后照常打开 Arc 即可。

### 常用命令
```sh
# 查看当前状态
python3 arc_forever.py status

# 恢复原始未修改版本
python3 arc_forever.py restore

# 导出侧边栏 Spaces 与置顶标签为书签
python3 tools/export_sidebar.py --output ./arc-bookmarks
```

## 开源许可

本项目基于 [MIT License](LICENSE) 开源。
