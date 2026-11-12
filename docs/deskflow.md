# Deskflow 模块

Deskflow 用于多台电脑共享键盘和鼠标，已作为独立的 `deskflow` 模块接入 Debian 13 / Arch 的统一入口。

在 curl 入口的菜单中选择第 **13** 项，或在已下载的项目目录执行：

```sh
./install.sh --only deskflow           # 只预览
./install.sh --check --only deskflow   # 检查系统
./install.sh --apply --only deskflow   # 实际安装
```

也包含在 `apps` 分组和推荐配置中；可用 `--skip deskflow` 排除。菜单仍默认不选模块，输入 `i` 才安装。

## 来源

- **Arch Linux**：使用官方仓库的 `deskflow` 包，依赖由 pacman 处理；已有软件包时跳过，不单独刷新同步数据库，不自动升级整台系统。
- **Debian 13 x86_64**：使用 Deskflow 官方发布的 `deskflow-1.27.0-debian-trixie-x86_64.deb`，包内版本 `1.27.0.0`。下载后校验固定 SHA256、包名、版本与 amd64 架构，再交给 APT 安装依赖。为原生 Wayland 界面补齐 `qt6-wayland`。已有相同或更高版本时跳过 Deskflow，只补缺失的运行依赖。

Debian 的包及依赖来自匹配 Trixie 的上游构建和系统软件源，不添加 sid / testing 源。安装使用 `--no-remove`，遇到需要移除其他软件的依赖方案时停止。包先下载校验，再开始当前所选模块的系统变更；准备后若安装状态意外改变，需要重新运行。

Debian 上游版本、URL 与校验值保存在 `profiles/common.json` 的 `system_apps.Deskflow.debian13` 中，更新版本时须一并更新。APT 缓存中的安装文件由正常的 APT 缓存维护处理。

官方来源：[Deskflow v1.27.0 发布](https://github.com/deskflow/deskflow/releases/tag/v1.27.0)、[Arch 官方包](https://archlinux.org/packages/extra/x86_64/deskflow/)。

## 安装后的配置

从应用列表打开 Deskflow，自行选择服务器或客户端，并设置目标地址、配对和所需桌面授权。模块只负责安装，不自动配置连接、不自动启动键鼠共享，也不复制其他设备的身份或证书。

已有 `~/.config/Deskflow/` 等用户配置保持原样。公共安装预设不包含服务器地址、设备名、TLS 私钥或信任列表。

## 验证范围

已校验 Deskflow 官方 Trixie 包的 SHA256 和控制信息，并在 Debian 13 上通过 APT 依赖模拟，未出现额外删除。两台测试机已安装 Deskflow，实际执行本模块均正确跳过已有版本，软件包列表保持不变；未通过新模块强制重装应用。Arch 的软件包此前已实际安装和运行。
