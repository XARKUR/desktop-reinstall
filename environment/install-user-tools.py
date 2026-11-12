#!/usr/bin/env python3
"""Install pinned fnm/uv binaries and configure the current user's Bash."""
import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
START = '# >>> desktop-reinstall development >>>'
END = '# <<< desktop-reinstall development <<<'
BLOCK = '''# >>> desktop-reinstall development >>>
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
if command -v fnm >/dev/null 2>&1; then
    eval "$(fnm env --use-on-cd --shell bash)"
fi
# <<< desktop-reinstall development <<<
'''


def install(selected=('fnm', 'uv')):
    if os.geteuid() == 0:
        raise RuntimeError('请以桌面用户运行 fnm/uv 安装。')
    if os.uname().machine != 'x86_64':
        raise RuntimeError('当前锁定的工具包适用于 x86_64。')
    home = Path.home()
    bashrc = home / '.bashrc'
    text = bashrc.read_text() if bashrc.exists() else ''
    if text.count(START) != text.count(END) or text.count(START) > 1:
        raise RuntimeError('Bash 安装标记不完整，请检查已有配置。')
    if START in text and text.index(START) > text.index(END):
        raise RuntimeError('Bash 安装标记顺序错误，请检查已有配置。')
    lock = json.loads((ROOT / 'sources.lock.json').read_text())
    cache = ROOT / 'cache'
    cache.mkdir(exist_ok=True)
    archives = {}
    for name in selected:
        entry = lock[name]
        target = cache / entry['file']
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != entry['sha256']:
            partial = target.with_suffix(target.suffix + '.partial')
            subprocess.run(['curl', '-4', '-fL', '--retry', '2', '--connect-timeout', '10',
                            '--max-time', '180', entry['url'], '-o', str(partial)], check=True)
            if hashlib.sha256(partial.read_bytes()).hexdigest() != entry['sha256']:
                partial.unlink()
                raise RuntimeError('工具包校验失败：' + name)
            partial.replace(target)
        archives[name] = target
    destination = home / '.local/bin'
    destination.mkdir(parents=True, exist_ok=True)
    backup = home / '.local/state/desktop-reinstall' / ('environment-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='desktop-tools-') as temp:
        staged = Path(temp)
        binaries = []
        if 'fnm' in selected:
            with zipfile.ZipFile(archives['fnm']) as archive:
                (staged / 'fnm').write_bytes(archive.read('fnm'))
            binaries.append('fnm')
        if 'uv' in selected:
            with tarfile.open(archives['uv']) as archive:
                for name in ['uv', 'uvx']:
                    member = archive.getmember('uv-x86_64-unknown-linux-gnu/' + name)
                    with archive.extractfile(member) as source:
                        (staged / name).write_bytes(source.read())
            binaries.extend(['uv', 'uvx'])
        for name in binaries:
            binary = staged / name
            binary.chmod(0o755)
            subprocess.run([str(binary), '--version'], check=True)
        for name in binaries:
            target = destination / name
            if target.exists() or target.is_symlink():
                shutil.copy2(target, backup / name)
            partial = destination / ('.' + name + '.install')
            shutil.copy2(staged / name, partial)
            partial.replace(target)
    if START in text:
        begin = text.index(START)
        finish = text.index(END, begin) + len(END)
        text = text[:begin] + BLOCK.rstrip('\n') + text[finish:]
    else:
        text = text.rstrip('\n') + '\n\n' + BLOCK
    if not bashrc.exists() or bashrc.read_text() != text:
        if bashrc.exists():
            shutil.copy2(bashrc, backup / '.bashrc')
        bashrc.write_text(text)
    print('、'.join(selected) + ' 和 Bash 已配置。备份：' + str(backup))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=['fnm', 'uv'])
    args = parser.parse_args()
    install((args.only,) if args.only else ('fnm', 'uv'))
