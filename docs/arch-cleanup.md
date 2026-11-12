# Arch GNOME 清理清单

实际清理已接入统一入口；完整流程见 [Arch 安装说明](arch-setup.md)，中文输入见 [配置说明](arch-locale.md)。

在 Arch 系统的项目目录中运行：

```sh
./install.sh --check --only cleanup
python3 modules/cleanup-arch.py     # 只读模拟
./install.sh --apply --only cleanup
```

不带 `--apply` 的独立清理入口只读取包状态，并用 `pacman -Rp --print-format '%n'` 模拟。真正执行时，统一入口会调用 sudo，重新读取和模拟，再以普通 `pacman -R` 移除逐个确认的目标，不递归清理依赖、不绕过依赖检查，并保留配置文件。模拟结果与清单不符或涉及保护项时停止。日历、时钟和核心桌面组件还有独立保护检查，不能通过误改配置移除。旧的 `python3 plan.py arch --installed` 也仍可用于只读模拟。

## 当前预设

保留日历、时钟、文件管理器、终端、计算器、文档和图片查看器、磁盘、系统监视器、GNOME 优化以及浏览器。GNOME Keyring、输入法、网络、SSH、声音、显卡驱动和核心运行库加入保护范围。

清理名单包含已确认不需要的办公、邮件、地图、音乐、默认播放器、相机、扫描、软件商店、家长控制界面和附带工具。部分旧版应用也保留在候选名单中，未安装的包自动跳过。`malcontent` 管理界面可移除，`libmalcontent` 共享库保留；设置使用的键盘布局查看器 `tecla` 保留。

当前系统模拟命中以下 20 个包，安装文件大小合计约 126 MiB，无额外连带删除：

| 类别 | 软件包 |
| --- | --- |
| 地图、联系人、连接工具 | `gnome-maps`、`gnome-contacts`、`gnome-connections` |
| 音乐和播放器 | `gnome-music`、`decibels`、`showtime` |
| 相机和扫描 | `snapshot`、`simple-scan` |
| 软件商店和家长控制界面 | `gnome-software`、`malcontent` |
| 字符、字体和日志查看器 | `gnome-characters`、`gnome-font-viewer`、`gnome-logs` |
| 欢迎和帮助 | `gnome-tour`、`gnome-user-docs`、`yelp` |
| 文件和媒体共享 | `gnome-user-share`、`rygel` |
| 原版天气和 Vim | `gnome-weather`、`vim` |

日历与时钟不在候选名单内，而且都在保护名单中。模拟前后的已安装包与版本列表一致。空间大小是这些软件包记录的安装大小总和，不包含依赖、缓存或用户文件；实际系统上的命中项随安装情况变化。

每次实际执行都会重新模拟并校验当前包状态。执行前后的包版本、显式安装名单和日志保存到 `/var/log/desktop-reinstall/arch-cleanup-*/`；需要管理员权限读取。执行后核对移除项、保留项和包数据库。再次执行时，已移除的应用会跳过。

## 执行验证

已在 Arch Linux / GNOME 51.1 / Python 3.14 上实际移除上述 20 个包。脚本核对实际删除项与目标完全一致，其余已安装包的版本未变化，日历、时钟和保护组件保留；包数据库检查通过，系统与用户服务均无失败项，Wayland 会话继续运行。重复模拟时已无待清理项。

自动测试还覆盖保护名单误改、额外删除、执行失败记录和平台入口隔离。验证结果见仓库根目录 `VALIDATION.json`。
