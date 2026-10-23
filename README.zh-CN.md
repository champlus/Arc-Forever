# Arc Forever — Arc 浏览器账户停用后继续使用

**让 Arc 浏览器在 2026 年 12 月 22 日账户停用后仍可使用本地认证的 macOS 原地修改工具，支持恢复。** Arc Forever 直接修改已安装的 Arc，保留应用名称、界面、Bundle ID 和原有浏览器配置，不额外生成 App。项目仅发布源代码和修改工具，不分发 Arc 安装包。

[English](README.md) · [兼容性与验证结果](docs/compatibility.md) · [技术原理](docs/architecture.md) · [Arc 官方停用公告](https://arc.net/)

**v0.1.0 为实验性预发布版本。** 在原本已关闭 SIP 的 macOS 15.7.4、Apple Silicon 上，Arc 1.170.0 的 `framework` 策略已通过原地修改、原配置正常启动、HTTPS 浏览、恢复及再次应用验证；原有 Spaces、标签、收藏和已启用的内容扩展仍可见，未观察到钥匙串提示。两种策略也均通过私有配置测试。默认启用 SIP 的系统，以及真实 Cookie、密码和通行密钥的直接检查仍未验证。详见[验证记录](docs/compatibility.md)；无法提前保证覆盖未来所有停用机制。

## 安装与使用

需要 macOS、Python 3 和 Apple Command Line Tools（`xcode-select --install`）。需要现有 Arc 配置中保留已登录身份缓存；本工具不能替代首次安装或登录。先退出 Arc，并另行备份浏览器数据。

希望双击操作时，下载或克隆仓库后，在 Finder 中打开 [Arc Forever.command](Arc%20Forever.command)，通过终端里的中英双语菜单选择应用修改、恢复或检查状态。它调用同一套 Python CLI，不生成额外 App。

使用命令行时，下载工具、检查当前版本，再应用修改：

```sh
git clone https://github.com/ChambersXDU/Arc-Forever.git
cd Arc-Forever
python3 arc_forever.py status
python3 arc_forever.py apply
```

完成后按原来的方式打开 Arc。默认目标是 `/Applications/Arc.app`；其他安装位置可向各命令传入 `--app /path/to/Arc.app`。工具不重定向 `HOME`、不新建浏览器配置、不使用模拟钥匙串，也不修改 `Info.plist`。

恢复原应用文件：

```sh
python3 arc_forever.py restore
```

默认备份目录为 `~/Library/Application Support/Arc Forever/Backups`，保存工具将修改的文件、签名资源、完整性哈希，以及必需的本地认证状态私有快照；它不是完整浏览器数据备份。使用补丁期间请保留备份：身份缓存缺失时，guard 可通过应用内记录找到快照并恢复。可用 `apply --backup-dir /path/to/backups` 指定其他目录。操作中断且应用内修改凭据缺失时，可使用 `restore --backup /path/to/specific-backup`。若修改后的载体已被更新或替换，恢复命令会拒绝覆盖该安装。

## 签名与系统兼容性

默认 `--strategy auto` 自动选择两种注入方式：

| 策略 | 选择条件 | 签名影响 |
| --- | --- | --- |
| `framework` | 仅在 SIP **原本已关闭**，且该构建的兼容库已经验证时选择。 | 修改兼容库，保留主程序原始厂商签名与权限声明；整个应用包的原始资源封印不再匹配。 |
| `main` | 其他受支持的安装，包括启用 SIP 的系统。 | 修改主程序并以 ad-hoc 签名重新签名，保留 hardened runtime，关闭该程序的 library validation；Chromium 辅助程序和 ArcCore 保留原签名。 |

**工具从不关闭或更改 SIP，也不要为了本工具关闭 SIP。** 可通过 `apply --strategy main` 或 `apply --strategy framework` 明确选择；启用 SIP 时会拒绝 `framework`。使用前查看[已测试配置](docs/compatibility.md)。

主程序重新签名后无法保留厂商签名身份及受限权限，macOS 可能重新请求已有钥匙串项目的访问权限；依赖厂商权限的通行密钥、CloudKit 等功能也可能受到影响。不能保证在默认安全配置的 macOS 上完全无感；签名校验通过也不代表所有浏览器功能均未改变。

## 本地使用的原理

Guard 从 Arc 已有认证状态提供本地 Firebase 用户，防止远程账户失效清除本地身份。请求云令牌时返回离线错误，不生成有效令牌，也不恢复服务端账户。Guard 还在进程内覆盖已追踪的强制退出登录与更新提示功能开关，并禁用已支持的自动更新路径；这些覆盖不会持久化改写偏好设置。

Arc Sync 等厂商云服务不会恢复。`framework` 保留现有 CloudKit 路径；`main` 无法重建厂商 CloudKit 权限，使用报告账户不可用的本地适配器。细节见[技术原理](docs/architecture.md)。

## 常见问题

**能否绕过 Arc 账户停用限制？** 工具处理本地客户端认证及已经定位的强制退出路径，让本地浏览使用本地身份；无法恢复远程账户、云同步或已经关闭的服务。未来的停用行为仍需实际观察。

**标签、Spaces、Cookie 和密码会搬到哪里？** 工具保留现有数据目录，不迁移或改写浏览器配置。不过签名变化仍可能影响钥匙串保护的数据访问，请以兼容性记录中的会话和密码测试结果为准；文件未变不等于访问权限必然不变。

**是否持续维护浏览器内核？** 不维护。保留旧版 Arc 也会固定 Chromium 的安全与网站兼容水平，本项目不提供后续 Chromium 安全更新。更新 Arc 可能覆盖补丁或安装尚未支持的版本。

## 开发与反馈

```sh
python3 -m unittest discover -s tests -v
```

macOS CI 运行 Python 测试与原生认证测试程序；当前本地验证已通过 16 项 Python 测试和两种 CloudKit 配置的原生测试。浏览器检查覆盖 HTTPS 导航、JavaScript 交互、重启后的存储恢复、运行时功能开关覆盖和原文件精确恢复；具体配置与限制见[兼容性页面](docs/compatibility.md)。

反馈请提供 macOS 版本、CPU 架构、Arc 版本与构建号、工具版本及脱敏错误。不要上传浏览器配置、认证状态、历史、Cookie、钥匙串内容、备份或 Arc 二进制。Git 忽略的 `.local/` 目录仅留在本地。

Arc Forever 与 The Browser Company 无隶属关系。项目源代码使用 [MIT 许可证](LICENSE)；Arc 及其第三方组件仍适用各自的许可证。
