# 来源与许可

本仓库的安装器、配置和测试采用 MIT 许可证，见 LICENSE。

安装器会按 profiles/common.json 中的固定提交下载以下独立项目；这些项目及其包含的上游资源继续适用各自的许可证：

- https://github.com/XARKUR/gnome-appearance
- https://github.com/XARKUR/gnome-weather-local
- https://github.com/XARKUR/gnome-lunar
- https://github.com/XARKUR/gnome-monitor

Docker、fnm、uv 和发行版软件包分别适用各自的许可证。本仓库不打包这些软件的二进制；environment/docker.asc 是 Docker 官方公开的软件源签名验证密钥，其来源、指纹和校验值记录在 environment/sources.lock.json。

Arch 的 Dash to Dock 从 GNOME 官方扩展站按固定版本与 SHA256 下载，适用其 GPL-2.0-or-later 许可证：https://extensions.gnome.org/extension/307/dash-to-dock/ 。不随本仓库打包扩展源码或二进制。
