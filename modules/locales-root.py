#!/usr/bin/env python3
"""Generate configured locales and set the desktop account language."""
import argparse
import datetime
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--user', required=True)
    parser.add_argument('--generate-only', action='store_true')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise RuntimeError('语言生成需要管理员权限。')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    os_id = release.get('ID', '').strip('"')
    if os_id not in ('debian', 'arch') or (os_id == 'debian' and release.get('VERSION_ID', '').strip('"') != '13'):
        raise RuntimeError('此语言模块适用于 Debian 13 或 Arch Linux。')
    data = json.loads(args.profile.read_text())
    if data.get('os_id', os_id) != os_id:
        raise RuntimeError('语言配置与当前发行版不匹配。')
    account = pwd.getpwnam(args.user)
    if account.pw_uid == 0:
        raise RuntimeError('请选择普通桌面用户。')
    config = data['localization']
    locales = config['generated_locales']
    if config['language'] not in locales or not all(re.fullmatch(r'[a-z]{2,3}_[A-Z]{2}\.UTF-8', name) for name in locales):
        raise RuntimeError('语言预设需要有效的 UTF-8 locale。')
    backup = Path('/var/backups/desktop-reinstall') / ('locale-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, mode=0o700)
    generated = subprocess.check_output(['locale', '-a'], text=True)
    normalized = lambda text: text.lower().replace('-', '')
    missing = [name for name in locales if normalized(name) not in map(normalized, generated.splitlines())]
    if missing:
        target = Path('/etc/locale.gen')
        text = target.read_text() if target.exists() else ''
        if target.exists():
            shutil.copy2(target, backup / 'locale.gen')
        lines = text.splitlines()
        for name in missing:
            enabled = name + ' UTF-8'
            for i, line in enumerate(lines):
                if line.lstrip('# ').strip() == enabled:
                    lines[i] = enabled
                    break
            else:
                lines.append(enabled)
        target.write_text('\n'.join(lines) + '\n')
        subprocess.run(['locale-gen'], check=True)
    if args.generate_only:
        return
    account_file = Path('/var/lib/AccountsService/users') / args.user
    if account_file.exists():
        shutil.copy2(account_file, backup / 'account')
    subprocess.run(['busctl', '--system', 'call', 'org.freedesktop.Accounts',
                    '/org/freedesktop/Accounts', 'org.freedesktop.Accounts',
                    'FindUserByName', 's', args.user], check=True)
    subprocess.run(['busctl', '--system', 'call', 'org.freedesktop.Accounts',
                    '/org/freedesktop/Accounts/User' + str(account.pw_uid),
                    'org.freedesktop.Accounts.User', 'SetLanguage', 's', config['language']], check=True)


if __name__ == '__main__':
    main()
