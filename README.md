# GNOME 桌面重装流程

把个人重装流程串成一个入口：清理默认应用 → 中文和输入法 → 基础工具 → 开发环境 → 外观 → 天气与扩展。可以整套执行，也可以只选需要的模块。

Debian 13 和 Arch Linux x86_64 均已接入清理、中文输入、基础工具、开发环境、外观、天气和扩展模块。需要 Python 3、sudo，以及当前用户的管理员权限；安装桌面组件时需要已登录 GNOME，会下载资源的模块需要联网。桌面组件支持已验证的 GNOME 48 / 51；Debian 13 默认是 48。请在自己的桌面终端以普通用户运行，需要管理员权限时才会提示输入密码。

## 使用

直接在普通用户的 GNOME 桌面终端运行（不要在整条命令前加 sudo）：

```sh
curl -fsSL https://raw.githubusercontent.com/XARKUR/desktop-reinstall/main/install.sh | sh
```

入口自动识别 Debian 13 或 Arch Linux x86_64，下载程序后显示模块菜单，不需要先安装 Git。需要已有 curl、Python 3 和 sudo。

菜单默认不选任何模块：输入编号切换选择，例如 `1 2 7-10`，也可以输入模块名或分组。`a` 全选，`r` 选择推荐配置，`c` 清空，`p` 只预览，`i` 执行当前选择，`q` 退出。按回车不会自动安装；只有输入 `i` 才开始执行。

菜单和后续命令通过终端接收输入，不会把管道中的脚本内容当成回答。下载文件在结束或失败后清理，安装状态、缓存与备份仍保存到下文列出的位置。

也可以克隆项目或 [下载 ZIP](https://github.com/XARKUR/desktop-reinstall/archive/refs/heads/main.zip) 后使用：

```sh
git clone https://github.com/XARKUR/desktop-reinstall.git
cd desktop-reinstall
./install.sh --menu              # 打开同一个模块选择菜单
```

本地直接运行 `./install.sh` 仍默认只预览。无需交互的远程预览也可以传参数：

```sh
curl -fsSL https://raw.githubusercontent.com/XARKUR/desktop-reinstall/main/install.sh | sh -s -- --plan --only environment
```

新系统需要联网访问 Debian、GitHub 与 Docker 官方源；本项目不配置网络代理。

```sh
./install.sh                       # 查看整套计划
./install.sh --list                # 查看模块名称
./install.sh --check               # 只检查系统和桌面会话
./install.sh --apply               # 执行对应系统的全部默认模块
```

按模块选择时，用逗号分隔。先省略 `--apply` 查看本次选择，确认内容后再加上它。

```sh
./install.sh --only cleanup,locale,tools
./install.sh --apply --only cleanup,locale,tools
./install.sh --apply --only environment
./install.sh --apply --only fnm
./install.sh --apply --only deskflow
./install.sh --apply --only appearance,weather,lunar,monitor
./install.sh --apply --skip cleanup,docker
```

参数顺序不改变执行次序。下表为两种系统共用的模块清单，每个模块按发行版补齐依赖。Arch 使用 pacman 官方仓库，Debian 使用 APT；不会自动安装 AUR 助手。

在 Arch 上分别清理和配置中文输入：

```sh
./install.sh --check --only cleanup
python3 modules/cleanup-arch.py     # 实际查询当前包并模拟删除
./install.sh --apply --only cleanup
./install.sh --check --only locale
./install.sh --apply --only locale
```

入口默认按当前系统选择配置，也可通过 `--profile profiles/arch.json` 显式指定。

## 模块

| 名称 | 内容 |
| --- | --- |
| `cleanup` | 清理已确认不需要的默认应用；保留日历、时钟和桌面基础组件 |
| `locale` | 生成中英文 UTF-8 locale，当前用户切换简体中文，安装 Noto CJK / Emoji、IBus 智能拼音，保留英文键盘与已有输入源 |
| `tools` | 日历、时钟、优化、官方“扩展”、文件管理器、终端、计算器、文本编辑器、系统监视器、磁盘、归档和查看器 |
| `docker` | 官方稳定源 Docker Engine、Compose、Buildx；Debian 使用 Docker 官方源，Arch 使用官方仓库；开机启动，当前用户加入 docker 组 |
| `fnm` | 固定版本的 fnm，配置 Bash；**不安装 Node.js** |
| `uv` | 固定版本的 uv / uvx，配置 Bash；不额外下载 Python |
| `appearance` | Orchis-Dark、按系统选择 Debian / Arch 活动按钮、Tela-dark 与基础图标、Breeze 24、User Themes、GTK4 全局换肤 |
| `weather` | Gnome Weather 应用和日历天气卡片 |
| `lunar` | Gnome Lunar，顶栏、月历与日期详情 |
| `monitor` | Gnome Monitor，资源监控和自动显卡型号识别 |
| `dock` | Dash to Dock：Debian 系统包、Arch 官方扩展站固定版本；关闭压力触发 |
| `appindicator` | AppIndicator 托盘扩展，使用发行版实际 UUID |
| `deskflow` | Deskflow 键鼠共享：Arch 官方包；Debian 13 固定上游 Trixie 包与 SHA256 |

也可以选择分组：`environment` = Docker / fnm / uv；`apps` = 基础工具 / 天气 / Deskflow；`extensions` = 农历 / 监控 / Dock / 托盘。天气模块自身已经包含日历卡片扩展。Deskflow 在交互菜单中为第 13 项，加入推荐配置；仍需自行勾选或输入 `r`。

初次安装扩展、修改语言或加入 docker 组后，保存工作并注销、重新登录。Wayland 下需要重新登录来加载首次安装的扩展。输入源使用 `Super+Space` 切换。

Dock 预设为底部、48 像素图标、智能隐藏，关闭 `require-pressure-to-show`。安装会应用公共清单中列出的这些偏好。天气首次使用需要在应用中添加地点。外观模块会应用预设，包括 GTK4 全局主题；农历和监控首次安装应用清单中的初始偏好，后续保留已有设置。Arch 的空白监控配置会通过项目自己的发现后端自动识别 GPU，显示利用率、显存和可用温度；已有设备选择保留，不拷贝其他机器的设备标识。

## 修改选择

- `profiles/debian13.json`：清理名单、保护名单、中文输入和基础工具包。
- `profiles/common.json`：默认模块、Docker 选项和四个桌面项目的固定提交。
- `environment/sources.lock.json`：fnm / uv 版本、官方下载地址和校验值。

想保留某个附带应用，从清理名单移除即可。清理会先模拟 APT 删除，遇到受保护组件、未经允许的连带删除或替换安装时停止；不执行笼统的 `autoremove`。默认移除办公套件、邮件、地图、部分媒体应用、软件商店、Seahorse 管理界面、XTerm 和附带 Vim 等；保留 GNOME Keyring、网络、SSH、日历和时钟。

Docker 组具有管理宿主系统的权限，可在公共配置中关闭 `add_user_to_group`。发现已有 Docker 发行版包、containerd 或 runc 冲突时，模块会停止让使用者处理已有容器环境。Docker 从官方稳定源安装可用版本；fnm / uv 使用锁定版本，两份文件中的版本需要同步修改。

只选天气而不选中文模块时，会按需要生成中文 locale 和安装字体，以支持天气应用的中文界面，但不会修改当前用户的界面语言。中文模块按新装 GNOME 的原生 IBus 配置；已有自定义输入框架应先自行检查。

显卡驱动、turing-unlock、额外应用、系统安装和系统升级由各自流程处理。Arch 各模块均已接入，详见 [Arch 完整安装说明](docs/arch-setup.md)、[清理说明](docs/arch-cleanup.md) 和 [中文输入说明](docs/arch-locale.md)。

Deskflow 的来源、版本与使用说明见 [Deskflow 模块](docs/deskflow.md)。

## 来源、记录和重试

外观、天气、农历和监控会先下载清单指定的 GitHub 提交，再开始清理和安装。下载失败时不会先清理应用。项目归档缓存位于 `${XDG_CACHE_HOME:-~/.cache}/desktop-reinstall/`，下载缓存带 SHA256 完整性记录；fnm / uv 使用发布文件的固定 SHA256 校验。

执行过程中任一模块出错就停止后续步骤，已完成的步骤不会自动回滚。处理错误后可以重新执行同样命令：包安装会检查缺失项，组件安装复用各项目自身的重复执行和备份机制。

- 总流程完成状态、命令与修改前的 GNOME 设置：`${XDG_STATE_HOME:-~/.local/state}/desktop-reinstall/run-*/`。
- fnm / uv 二进制与 Bash 备份：`~/.local/state/desktop-reinstall/environment-*/`。
- locale 与账户语言文件备份：`/var/backups/desktop-reinstall/locale-*/`。
- Docker 源文件备份和安装版本：`/var/backups/desktop-environment-*/`。
- Arch 清理前后的包清单、实际移除项及日志：`/var/log/desktop-reinstall/arch-cleanup-*/`，需要管理员权限读取。
- 外观与各扩展还会使用自身项目的备份目录。Debian 清理模块在执行时显示自己的日志目录。

总流程记录不等于系统快照，也不保存终端完整输出。需要完整安装日志时，可以自行保存终端输出。

## 验证范围

已做参数选择、只读预览、失败停止、依赖补齐、清理保护、locale 文件生成、发行版扩展 UUID 和归档路径检查，并通过模拟系统操作测试整套模块调度。四个固定提交的源码已实际下载、解包并核对入口。

**尚未在一台全新 Debian 13 上连续执行整套安装**。Arch 已实际完成 20 个目标包的清理，并核对日历、时钟、包数据库和桌面服务；完整桌面与开发环境的实测范围见 `VALIDATION.json`。此前独立组件的测试记录保留在相应项目及 `environment/VALIDATION.json`。

开发检查：

```sh
python3 -m unittest discover -s tests -v
```

## 许可

安装器采用 [MIT 许可证](LICENSE)。下载的独立项目和第三方资源保留各自许可，见 [来源说明](NOTICE.md)。
