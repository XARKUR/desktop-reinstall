#!/bin/bash
set -euo pipefail
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [[ ${1:---plan} == --plan ]]; then
    echo 'Debian 13：Docker 官方源 → Docker Engine/Compose/Buildx → docker 用户组'
    echo '用户环境：fnm + uv/uvx → Bash PATH 和 fnm 自动切换'
    echo 'Node.js 版本按项目自行选择。uv 使用项目虚拟环境。'
    exit 0
fi
[[ ${1:-} == --apply && $# == 1 ]] || { echo '用法：install.sh [--plan|--apply]' >&2; exit 1; }
[[ $(id -u) != 0 ]] || { echo '请以桌面用户运行。' >&2; exit 1; }
. /etc/os-release
[[ $ID == debian && $VERSION_ID == 13 && $(uname -m) == x86_64 ]] || {
    echo '此安装入口适用于 Debian 13 x86_64。' >&2
    exit 1
}
sudo bash "$project_dir/install-docker-debian.sh" "$(id -un)"
python3 "$project_dir/install-user-tools.py"
echo 'READY：Docker、fnm 和 uv 已安装。'
