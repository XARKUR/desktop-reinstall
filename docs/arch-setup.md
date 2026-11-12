# Arch GNOME 完整安装

起点为已安装并登录 GNOME 48 / 51 的 Arch Linux x86_64 桌面，需要 Python、sudo 和联网。以普通桌面用户运行：

```sh
./install.sh                              # 只显示完整计划
./install.sh --check                      # 只检查环境
./install.sh --apply                      # 执行完整流程
./install.sh --apply --skip cleanup,locale # 已完成前两项时继续
./install.sh --apply --only appearance,extensions
./install.sh --apply --only environment
```

模块次序与 Debian 版一致：清理 → 中文输入 → 基础工具和桌面偏好 → Docker / fnm / uv → 外观 → 天气 → 农历 → 监控 → Dock → 托盘。先准备所选项目的固定版本资源，下载失败时不会先清理应用。

## 发行版适配

| 内容 | Arch 的做法 |
| --- | --- |
| 默认应用清理 | 逐个确认的包名，保留日历、时钟、GNOME Keyring 与系统组件；无递归依赖清理 |
| 中文输入 | IBus 智能拼音、Noto CJK / Emoji；当前用户中文界面，保留英文键盘 |
| 基础工具 | 日历、时钟、优化、GNOME“扩展”、Console、文件管理器、计算器、文本编辑器、磁盘、监视器、归档和查看器 |
| GNOME 偏好 | 顶栏显示星期、日期和秒，月历显示周数，保留桌面基础应用的有效 Dock 入口；具体值见 profiles/arch.json |
| 文档查看器 | 使用 Arch 的 Papers，Debian 使用 Evince |
| Docker | Arch 官方仓库 docker、docker-compose、docker-buildx；开机启动，按配置加入 docker 组 |
| fnm / uv | 使用与 Debian 相同的固定官方下载文件和 SHA256；配置 Bash，不预装 Node.js 或下载 Python |
| 外观 | Orchis-Dark、Arch 活动按钮、Tela-dark 与基础图标、Breeze 24、User Themes、GTK4 全局换肤 |
| 天气 | 同一个独立应用与日历卡片项目；首次使用在应用内添加地点 |
| 农历 | 同一个 GNOME 48 / 51 兼容项目；首次安装设置农历、干支和日期详情 |
| 资源监控 | 同一个项目；首次使用自动发现 AMD / Intel / NVIDIA 可用指标，型号来自当前机器的发现后端 |
| Dock | 从 GNOME 官方扩展站下载固定 v110，校验 SHA256 和 GNOME 版本；安装到用户目录并备份旧版本 |
| 托盘 | Arch 官方 gnome-shell-extension-appindicator，UUID 为 appindicatorsupport@rgcjonas.gmail.com |

Arch 保留原生 Console 和现有浏览器，不批量复制其他设备上的应用启动项。硬件驱动由基础系统或对应的独立项目管理，不在通用流程中安装 NVIDIA 驱动。

## 偏好与重复运行

外观与 Dock 会应用清单中的配置。农历和监控的初始偏好仅在首次安装时应用；后续安装保留已有用户偏好。监控发现脚本只在设备列表为空时初始化当前机器的 GPU，不包含固定显卡名称、卡号或其他设备的路径。已有设备选择保留。新装的系统会重新发现硬件。

Dock 预设为底部、48 像素、智能隐藏，并关闭鼠标边缘压力触发。用户目录安装的 Dock 会用自身的 schema 应用设置；托盘使用发行版的实际 UUID。

系统包使用已有 pacman 数据库安装缺失项，不执行单独的 `pacman -Sy`，不自动安装 AUR 助手，也不把 AUR 包名交给 pacman。遇到镜像版本过期时，应先按 Arch 的正常流程完成系统更新再重试。Orchis 的 Arch 依赖不包含 AUR 中的 GTK2 Murrine 引擎。

安装结束后保存工作、注销并重新登录，加载新扩展、主题和 docker 组权限。Wayland 下不使用 Alt+F2 的 r 重载。

## 记录和验证

总流程记录、修改前的 GNOME 设置和旧版用户 Dock 的备份位于 `~/.local/state/desktop-reinstall/run-*/`。各项目还保留自己的更新备份。Docker 安装版本及变更前组信息位于 `/var/backups/desktop-environment-*/`。

自动测试检查发行版包名、Docker 入口、用户扩展归档校验和路径、旧版 Dock 备份、GPU 自动发现和偏好保留。实际验证范围见根目录 `VALIDATION.json`。

使用者的天气地点、温度单位、设备列表和地址不包含在公共安装预设中。更换机器时可以在应用中添加地点，或自行迁移对应用户设置。

已在全新 Arch / GNOME 51.1 / Python 3.14 上分阶段完成全部模块：六个扩展均处于 ACTIVE，图标检查无缺失，天气返回 168 小时与 7 天预报，Docker 普通用户构建、容器运行、Compose 及 uv 锁定运行均通过。主题的原生工作区指示器重叠问题已修复并经使用者确认。处于省电休眠的 GPU 可能暂时没有占用或温度读数，安装器保留系统省电设置。
