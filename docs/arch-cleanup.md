# Arch GNOME 清理清单

目前只接入清单和只读模拟；统一 `install.sh --apply` 仍仅用于 Debian 13。

在 Arch 系统的项目目录中运行：

```sh
python3 plan.py arch --installed
```

该命令读取已安装包，并用 `pacman -Rp --print-format '%n'` 预览删除目标，不使用 sudo、不实际卸载、不递归清理依赖。保护项或未经允许的额外删除出现在模拟结果中时会报错。

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

尚未执行实际卸载。今后执行清理前应重新生成模拟结果，不复用本页记录直接删除。
