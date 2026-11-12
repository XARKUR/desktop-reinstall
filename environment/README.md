# 开发环境（Debian 13 / Arch）

以普通桌面用户运行，安装 Docker Engine、Compose、Buildx、fnm 和 uv。统一入口在项目根目录：

```sh
./install.sh --apply --only environment
```

下面 `environment/install.sh` 是原有 Debian 独立入口；Arch 请使用上面的统一入口。

```sh
./install.sh --plan
./install.sh --apply
```

Debian 的 Docker 通过官方 trixie 软件源安装；Arch 使用发行版官方仓库的 docker、docker-compose、docker-buildx。两者均设置开机启动，当前用户加入 docker 组。该组具有管理宿主机的权限，现有桌面会话在注销后重新登录可获得新组权限。遇到已有 Docker 发行版包或 containerd/runc 冲突时会先停止，供使用者检查已有环境。

fnm 与 uv/uvx 安装到 `~/.local/bin/`，Bash 会加载用户 PATH 与 `fnm env --use-on-cd --shell bash`。fnm 只安装管理器，具体 Node.js 版本由各项目选择。uv 使用项目虚拟环境；其他 Python 版本可按项目需要用 uv 下载管理。

fnm/uv 的版本、官方下载地址和 SHA256 固定在 `sources.lock.json`。缓存位于 `cache/`，缺少时自动从官方发布页下载并校验。Docker 使用官方稳定软件源中的可用版本，通过 APT 维护更新。Docker 签名密钥的 SHA256 和指纹也保存在清单中。

脚本重复执行会更新受管理的 Bash 区块，已有其他 Bash 配置保留。文件备份位于 `~/.local/state/desktop-reinstall/environment-*/`，Docker 软件源备份及安装版本记录位于 `/var/backups/desktop-environment-*/`。

常用操作可在安装后打开的新终端中执行。

```sh
docker compose version
docker buildx version
fnm --version
fnm install --lts           # 按需选择 Node.js
uv --version
uv venv                    # 在当前项目创建虚拟环境
uv sync                    # 按项目锁文件安装依赖
```

参考 [Docker Debian 安装说明](https://docs.docker.com/engine/install/debian/)、[fnm Shell 配置](https://github.com/Schniz/fnm#shell-setup) 和 [uv 安装说明](https://docs.astral.sh/uv/getting-started/installation/)。
