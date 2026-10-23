# Arc Forever

**让 Arc 浏览器在官方账户停用后仍可在 macOS 上继续本地使用。**

Arc Forever 是一个轻量级、可逆的原地补丁工具。它通过在本地提供认证支持，让已登录的 Arc 浏览器摆脱对官方账号服务器的依赖，完整保留现有的 Spaces、标签页、收藏夹与浏览器配置。

[English](README.md) · [兼容性说明](docs/compatibility.md) · [技术原理](docs/architecture.md) · [Arc 官方公告](https://arc.net/)

## 特性

- **原地修改，随时恢复**：直接作用于已安装的 Arc.app，自动备份关键文件，可随时一键完整恢复。
- **保留完整配置与界面**：不更改 Bundle ID、应用名称或数据目录，Spaces、置顶标签、扩展及历史记录均在原处。
- **本地身份保持**：阻止远程下线请求，在服务关闭后依然能以离线身份正常启动并浏览网页。
- **支持默认 SIP 环境**：适用于标准 macOS 系统安全配置，无需关闭系统完整性保护（SIP）。

## 快速开始

### 前提条件
- macOS
- Python 3 与 Command Line Tools（可在终端运行 `xcode-select --install` 安装）
- 本地已有登录过账号的 Arc 浏览器（操作前请先退出 Arc）

### 使用方法

**方式一：双击运行**
下载或克隆仓库后，在 Finder 中双击打开 [Arc Forever.command](Arc%20Forever.command)，按照终端菜单选择应用、恢复或查看状态。

**方式二：命令行**
```sh
git clone https://github.com/ChambersXDU/Arc-Forever.git
cd Arc-Forever

# 查看状态
python3 arc_forever.py status

# 应用补丁
python3 arc_forever.py apply

# 如需恢复原版
python3 arc_forever.py restore
```

应用完成后，像往常一样正常启动 Arc 即可。

## 备份与恢复

工具会在应用补丁时自动将原始文件备份至：  
`~/Library/Application Support/Arc Forever/Backups`

运行 `python3 arc_forever.py restore` 即可校验哈希并将应用恢复到修改前的原始状态。

## 注意事项

- **云端服务**：官方服务器停用后，Arc Sync 等依赖云端后端的功能将无法使用，浏览器仅作为本地单机浏览器运行。
- **钥匙串提示**：由于应用被重新签名，macOS 可能会在首次打开时弹出钥匙串访问提示，选择“始终允许”即可。
- **内核版本**：本项目旨在保持 Arc 现有功能的本地可用性，不维护或更新底层的 Chromium 内核。

## 开源许可

本项目基于 [MIT 许可证](LICENSE) 开源。Arc 及相关商标、组件所有权归 The Browser Company 所有。
