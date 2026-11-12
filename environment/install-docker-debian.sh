#!/bin/bash
set -euo pipefail
if [[ $(id -u) != 0 ]]; then
    echo '请通过主安装入口运行 Docker 安装。' >&2
    exit 1
fi
. /etc/os-release
[[ $ID == debian && $VERSION_ID == 13 ]]
task_user=${1:?需要桌面用户名}
add_group=${2:-true}
with_compose=${3:-true}
with_buildx=${4:-true}
id "$task_user" >/dev/null
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 - "$project_dir" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);lock=json.loads((root/'sources.lock.json').read_text())
assert hashlib.sha256((root/'docker.asc').read_bytes()).hexdigest()==lock['docker']['key_sha256'], 'Docker key checksum mismatch'
PY
for package in docker.io docker-compose docker-doc docker-buildx podman-docker containerd runc; do
    if [[ $(dpkg-query -W -f='${db:Status-Abbrev}' "$package" 2>/dev/null || true) == ii* ]]; then
        echo "发现与 Docker CE 冲突的已有包 $package，请先审阅现有容器环境。" >&2
        exit 1
    fi
done
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl
backup_dir=/var/backups/desktop-environment-$(date +%Y%m%d-%H%M%S-%N)
install -d -m 700 "$backup_dir"
for file in /etc/apt/keyrings/docker.asc /etc/apt/sources.list.d/docker.sources; do
    if [[ -f $file ]]; then cp -a --parents "$file" "$backup_dir"; fi
done
install -d -m 0755 /etc/apt/keyrings
install -m 0644 "$project_dir/docker.asc" /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<REPO
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: trixie
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
REPO
apt-get update
packages=(docker-ce docker-ce-cli containerd.io)
[[ $with_compose != true ]] || packages+=(docker-compose-plugin)
[[ $with_buildx != true ]] || packages+=(docker-buildx-plugin)
apt-get install -y --no-install-recommends "${packages[@]}"
systemctl enable --now docker
[[ $add_group != true ]] || usermod -aG docker "$task_user"
python3 - "$backup_dir" "${packages[@]}" <<'PY'
import subprocess,sys
from pathlib import Path
p=Path(sys.argv[1])/'installed-packages.txt'
p.write_text(subprocess.check_output(['dpkg-query','-W',*sys.argv[2:]],text=True))
PY
echo '所选 Docker 组件已安装，服务已启动。'
