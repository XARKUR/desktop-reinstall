#!/bin/bash
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo '请通过主安装入口运行 Docker 安装。' >&2; exit 1; }
. /etc/os-release
[[ $ID == arch && $(uname -m) == x86_64 ]]
task_user=${1:?需要桌面用户名}
add_group=${2:-true}
with_compose=${3:-true}
with_buildx=${4:-true}
[[ $(id -u "$task_user") != 0 ]]
for flag in "$add_group" "$with_compose" "$with_buildx"; do
    [[ $flag == true || $flag == false ]] || { echo 'Docker 开关必须为 true/false。' >&2; exit 1; }
done
if pacman -Qq podman-docker >/dev/null 2>&1; then
    echo '发现 podman-docker，请先检查已有容器环境。' >&2
    exit 1
fi
packages=(docker)
[[ $with_compose != true ]] || packages+=(docker-compose)
[[ $with_buildx != true ]] || packages+=(docker-buildx)
pacman -Si -- "${packages[@]}" >/dev/null
# Keep the existing repository snapshot; never perform a stand-alone -Sy.
pacman -S --needed --noconfirm -- "${packages[@]}"
backup_dir=/var/backups/desktop-environment-$(date +%Y%m%d-%H%M%S-%N)
install -d -m 700 "$backup_dir"
pacman -Q -- "${packages[@]}" > "$backup_dir/installed-packages.txt"
id "$task_user" > "$backup_dir/user-groups-before.txt"
systemctl enable --now docker
[[ $add_group != true ]] || usermod -aG docker "$task_user"
echo 'Docker、所选插件及开机启动已配置。新增的组权限在重新登录后生效。'
