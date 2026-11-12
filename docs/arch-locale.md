# Arch 简体中文与 IBus 智能拼音

已接入统一 `locale` 模块，面向已登录 GNOME 的 Arch Linux x86_64 用户。使用原生 IBus 集成，保留英文键盘及已有输入源。

```sh
./install.sh --only locale            # 查看模块计划
./install.sh --check --only locale    # 只检查系统与桌面会话
./install.sh --apply --only locale    # 实际配置
```

以普通桌面用户运行，软件安装、生成 locale 和账户语言设置需要 sudo 认证。Arch 默认模块目前为 `cleanup,locale`，需要只配置语言时请显式使用 `--only locale`。

## 配置内容

- 安装缺失的 `ibus`、`ibus-libpinyin`、`noto-fonts-cjk`、`noto-fonts-emoji`，并确保 `glibc`、`glib2`、`accountsservice` 存在。
- 生成 `zh_CN.UTF-8` 与 `en_US.UTF-8`，保留 `/etc/locale.gen` 中已有的其他语言设置。
- 通过 AccountsService 将当前桌面用户的语言设为简体中文，并设置中文区域格式。其他账户和 `/etc/locale.conf` 的系统默认语言保留。
- 向 GNOME 输入源追加英语（美国）与智能拼音 `libpinyin`，保留已有输入源并避免重复添加。
- 使用 GNOME 原生 IBus 会话；不额外写入输入法环境变量，也不另启一个输入法守护进程。

安装软件使用现有 pacman 同步数据库，先检查缺失包及仓库中是否可用，再安装缺失项；不执行单独的 `pacman -Sy`，也不自动升级整台系统。如果镜像找不到数据库对应版本，请先按 Arch 的正常流程完成系统更新，再重新运行本模块。

## 生效与检查

保存工作后注销并重新登录，使中文界面和新安装的输入法引擎完整加载。默认使用 `Super+Space` 切换输入源；选择智能拼音后输入 `nihao`，应能选择“你好”。拼音引擎内通常用 Shift 切换中英文，具体以输入法偏好为准。

```sh
locale -a
ibus list-engine
pacman -Q ibus ibus-libpinyin noto-fonts-cjk noto-fonts-emoji
gsettings get org.gnome.desktop.input-sources sources
gsettings get org.gnome.system.locale region
```

GNOME 的“设置 → 键盘 → 输入源”中应同时有英语（美国）和汉语（智能拼音）。新登录后的桌面环境应为 `LANG=zh_CN.UTF-8`；SSH 新会话使用什么语言还取决于 SSH 与登录环境，不应用 SSH 中的 LANG 单独判断桌面语言。

重复执行会跳过已安装的软件，保留已有输入源。语言文件与账户语言备份位于 `/var/backups/desktop-reinstall/locale-*/`；用户 GNOME 设置变更前的值位于 `~/.local/state/desktop-reinstall/run-*/settings-before.json`。

此流程面向新装 GNOME。已有 Fcitx 或手工设置输入法环境变量的系统，需要先核对自己的输入法配置。

## 验证记录

已在 Arch / GNOME 51.1 上实际安装和配置。重新登录后的桌面语言为 `zh_CN.UTF-8`，IBus 引擎列表包含智能拼音，输入源同时保留英文键盘；包数据库检查通过，用户服务无失败项，日历和时钟保留。程序检查覆盖引擎注册与桌面设置，尚未记录用户实际输入文字的确认。
