# Debian 13 GNOME 桌面安装流程

把个人重装流程串成一个入口：清理默认应用 → 中文和输入法 → 基础工具 → 开发环境 → 外观 → 天气与扩展。可以整套执行，也可以只选需要的模块。

适用于**已安装并登录 GNOME 的 Debian 13 x86_64 桌面**，需要联网、Python 3、sudo，以及当前用户的管理员权限。桌面组件支持已验证的 GNOME 48 / 51；Debian 13 默认是 48。请在自己的桌面终端以普通用户运行，需要管理员权限时才会提示输入密码。

## 使用

克隆项目（需要 Git），或从 [GitHub 下载 ZIP](https://github.com/XARKUR/desktop-reinstall/archive/refs/heads/main.zip) 并解压，然后进入项目目录。入口默认只预览，不安装或清理任何东西。

```sh
git clone https://github.com/XARKUR/desktop-reinstall.git
cd desktop-reinstall
```

新系统需要联网访问 Debian、GitHub 与 Docker 官方源；本项目不配置网络代理。

```sh
./install.sh                       # 查看整套计划
./install.sh --list                # 查看模块名称
./install.sh --check               # 只检查系统和桌面会话
./install.sh --apply               # 执行全部默认模块
```

按模块选择时，用逗号分隔。先省略 `--apply` 查看本次选择，确认内容后再加上它。

```sh
./install.sh --only cleanup,locale,tools
./install.sh --apply --only cleanup,locale,tools
./install.sh --apply --only environment
./install.sh --apply --only fnm
./install.sh --apply --only appearance,weather,lunar,monitor
./install.sh --apply --skip cleanup,docker
```

参数顺序不改变执行次序。所选模块统一按下表顺序执行，每个模块自动补齐自己的系统依赖。

## 模块

| 名称 | 内容 |
| --- | --- |
| `cleanup` | 清理已确认不需要的默认应用；保留日历、时钟和桌面基础组件 |
| `locale` | 生成中英文 UTF-8 locale，当前用户切换简体中文，安装 Noto CJK / Emoji、IBus 智能拼音，保留英文键盘与已有输入源 |
| `tools` | 日历、时钟、优化、官方“扩展”、文件管理器、终端、计算器、文本编辑器、系统监视器、磁盘、归档和查看器 |
| `docker` | 官方稳定源 Docker Engine、Compose、Buildx；开机启动，当前用户加入 docker 组 |
| `fnm` | 固定版本的 fnm，配置 Bash；**不安装 Node.js** |
| `uv` | 固定版本的 uv / uvx，配置 Bash；不额外下载 Python |
| `appearance` | Orchis-Dark、Debian 活动按钮、Tela-dark 与基础图标、Breeze 24、User Themes、GTK4 全局换肤 |
| `weather` | Gnome Weather 应用和日历天气卡片 |
| `lunar` | Gnome Lunar，顶栏、月历与日期详情 |
| `monitor` | Gnome Monitor，资源监控和自动显卡型号识别 |
| `dock` | Debian Dash to Dock，关闭边缘压力触发要求 |
| `appindicator` | Debian AppIndicator 托盘扩展，使用发行版实际 UUID |

也可以选择分组：`environment` = Docker / fnm / uv；`apps` = 基础工具 / 天气；`extensions` = 农历 / 监控 / Dock / 托盘。天气模块自身已经包含日历卡片扩展。

初次安装扩展、修改语言或加入 docker 组后，保存工作并注销、重新登录。Wayland 下需要重新登录来加载首次安装的扩展。输入源使用 `Super+Space` 切换。

Dock 只关闭 `require-pressure-to-show`，保留现有位置与隐藏方式。首次安装时使用扩展自己的默认设置。天气首次使用需要在应用中添加地点。外观模块会应用预设，包括 GTK4 全局主题；农历、天气和监控安装使用各自的默认设置，并保留已有用户偏好。

## 修改选择

- `profiles/debian13.json`：清理名单、保护名单、中文输入和基础工具包。
- `profiles/common.json`：默认模块、Docker 选项和四个桌面项目的固定提交。
- `environment/sources.lock.json`：fnm / uv 版本、官方下载地址和校验值。

想保留某个附带应用，从清理名单移除即可。清理会先模拟 APT 删除，遇到受保护组件、未经允许的连带删除或替换安装时停止；不执行笼统的 `autoremove`。默认移除办公套件、邮件、地图、部分媒体应用、软件商店、Seahorse 管理界面、XTerm 和附带 Vim 等；保留 GNOME Keyring、网络、SSH、日历和时钟。

Docker 组具有管理宿主系统的权限，可在公共配置中关闭 `add_user_to_group`。发现已有 Docker 发行版包、containerd 或 runc 冲突时，模块会停止让使用者处理已有容器环境。Docker 从官方稳定源安装可用版本；fnm / uv 使用锁定版本，两份文件中的版本需要同步修改。

只选天气而不选中文模块时，会按需要生成中文 locale 和安装字体，以支持天气应用的中文界面，但不会修改当前用户的界面语言。中文模块按新装 GNOME 的原生 IBus 配置；已有自定义输入框架应先自行检查。

显卡驱动、turing-unlock、额外应用、系统安装和系统升级由各自流程处理。Arch 的清理清单已整理，可用 `python3 plan.py arch --installed` 做只读模拟，详见 [Arch 清理说明](docs/arch-cleanup.md)。**这个执行入口仅用于 Debian 13**。

## 来源、记录和重试

外观、天气、农历和监控会先下载清单指定的 GitHub 提交，再开始清理和安装。下载失败时不会先清理应用。项目归档缓存位于 `${XDG_CACHE_HOME:-~/.cache}/desktop-reinstall/`，下载缓存带 SHA256 完整性记录；fnm / uv 使用发布文件的固定 SHA256 校验。

执行过程中任一模块出错就停止后续步骤，已完成的步骤不会自动回滚。处理错误后可以重新执行同样命令：包安装会检查缺失项，组件安装复用各项目自身的重复执行和备份机制。

- 总流程完成状态、命令与修改前的 GNOME 设置：`${XDG_STATE_HOME:-~/.local/state}/desktop-reinstall/run-*/`。
- fnm / uv 二进制与 Bash 备份：`~/.local/state/desktop-reinstall/environment-*/`。
- locale 与账户语言文件备份：`/var/backups/desktop-reinstall/locale-*/`。
- Docker 源文件备份和安装版本：`/var/backups/desktop-environment-*/`。
- 外观与各扩展还会使用自身项目的备份目录。清理模块在执行时显示自己的日志目录。

总流程记录不等于系统快照，也不保存终端完整输出。需要完整安装日志时，可以自行保存终端输出。

## 验证范围

已做参数选择、只读预览、失败停止、依赖补齐、清理保护、locale 文件生成、发行版扩展 UUID 和归档路径检查，并通过模拟系统操作测试整套模块调度。四个固定提交的源码已实际下载、解包并核对入口。

本次仅开发与验证脚本，**未在本机执行安装、清理或升级，也尚未在一台全新 Debian 13 上连续执行整套安装**。此前独立组件的测试记录保留在相应项目及 `environment/VALIDATION.json`。

开发检查：

```sh
python3 -m unittest discover -s tests -v
```

## 许可

安装器采用 [MIT 许可证](LICENSE)。下载的独立项目和第三方资源保留各自许可，见 [来源说明](NOTICE.md)。
