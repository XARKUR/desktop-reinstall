#!/bin/sh
# Local: default read-only plan. curl | sh: download the project and open the menu.
set -eu
if ! command -v python3 >/dev/null 2>&1; then
    echo '需要 Python 3，请先安装后重新运行。' >&2
    exit 1
fi
case "$0" in
    */install.sh|install.sh)
        project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
        if [ -f "$project_dir/installer.py" ] && [ -f "$project_dir/profiles/common.json" ]; then
            exec python3 "$project_dir/installer.py" "$@"
        fi
        ;;
esac
if [ "$#" -eq 0 ]; then
    set -- --menu
fi
project_temp=$(mktemp -d)
trap 'rm -rf -- "$project_temp"' 0
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
python3 - "$project_temp" "$@" <<'PYBOOTSTRAP'
import io
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request


def main(root, arguments):
    if os.geteuid() == 0:
        raise ValueError('请以普通桌面用户运行，不要给整条安装命令加 sudo。')
    release = platform.freedesktop_os_release()
    supported = release.get('ID') == 'arch' or (release.get('ID') == 'debian' and release.get('VERSION_ID') == '13')
    if not supported or platform.machine() != 'x86_64':
        raise ValueError('支持 Debian 13 或 Arch Linux x86_64。')
    terminal = None
    try:
        terminal = open('/dev/tty', 'r', encoding='utf-8')
    except OSError:
        if '--menu' in arguments:
            raise ValueError('模块菜单需要终端，请在桌面终端运行这条命令。仅预览可传 --plan。')
    try:
        print('已识别：' + ('Arch Linux' if release['ID'] == 'arch' else 'Debian 13') + ' x86_64', flush=True)
        print('正在下载安装程序…', flush=True)
        address = 'https://codeload.github.com/XARKUR/desktop-reinstall/tar.gz/refs/heads/main'
        for attempt in range(3):
            try:
                request = urllib.request.Request(address, headers={'User-Agent': 'desktop-reinstall-bootstrap'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = response.read(32 * 1024 * 1024 + 1)
                break
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(2)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError('安装程序归档超过大小限制。')
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as source:
            total = 0
            for index, member in enumerate(source):
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                    raise ValueError('安装程序归档包含不支持的路径或链接。')
                total += member.size
                if index >= 100000 or total > 128 * 1024 * 1024:
                    raise ValueError('安装程序解压超过大小限制。')
                destination = root.joinpath(*path.parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with source.extractfile(member) as stream, destination.open('xb') as output:
                        shutil.copyfileobj(stream, output)
                    destination.chmod(0o755 if member.mode & 0o111 else 0o644)
        entries = list(root.glob('*/installer.py'))
        if len(entries) != 1:
            raise ValueError('安装程序入口缺失或目录结构无效。')
        # Never let a menu or a child command consume the piped shell script.
        return subprocess.run([sys.executable, str(entries[0]), *arguments],
                              stdin=terminal if terminal is not None else subprocess.DEVNULL).returncode
    finally:
        if terminal is not None:
            terminal.close()


if __name__ == '__main__':
    try:
        sys.exit(main(Path(sys.argv[1]), sys.argv[2:]))
    except KeyboardInterrupt:
        print('\n已取消。', file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, tarfile.TarError) as error:
        print('停止：' + str(error), file=sys.stderr)
        sys.exit(1)
PYBOOTSTRAP
