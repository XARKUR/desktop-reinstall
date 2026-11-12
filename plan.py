#!/usr/bin/env python3
"""Preview a personal GNOME reinstall profile, optionally on a matching system."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess

PROFILES = Path(__file__).resolve().parent / 'profiles'


def load_profile(name):
    return json.loads((PROFILES / (name + '.json')).read_text())


def read_command(args):
    return subprocess.check_output(args, text=True, env={**os.environ, 'LC_ALL': 'C'})


def distro_id():
    release = platform.freedesktop_os_release()
    if release.get('ID') == 'arch':
        return 'arch'
    if release.get('ID') == 'debian' and release.get('VERSION_ID') == '13':
        return 'debian13'
    return None


def preview_cleanup(edition):
    config = edition['cleanup']
    debian = edition['manager'] == 'apt'
    if debian:
        rows = read_command(['dpkg-query', '-W', '-f=${binary:Package} ${db:Status-Abbrev}\\n'])
        installed = [row.split()[0] for row in rows.splitlines() if row.split()[1:2] == ['ii']]
    else:
        installed = read_command(['pacman', '-Qq']).splitlines()

    exact = set(config['remove_exact'])
    prefixes = tuple(config['remove_prefix'])
    targets = sorted(p for p in installed if p.split(':')[0] in exact or p.split(':')[0].startswith(prefixes))
    if not targets:
        print('当前系统命中 0 个清理候选。')
        return
    print(f'当前系统命中 {len(targets)} 个候选：' + ' '.join(targets), flush=True)
    if debian:
        output = read_command(['apt-get', '-s', '-o', 'APT::Get::AutomaticRemove=false', 'remove', *targets])
        if re.search(r'^Inst ', output, re.M):
            raise ValueError('包管理器提议同时安装其他软件，请检查清单。')
        planned = re.findall(r'^(?:Remv|Purg) (\S+)', output, re.M)
    else:
        planned = read_command(['pacman', '-Rp', '--print-format', '%n', '--', *targets]).splitlines()
    names = {p.split(':')[0] for p in planned}
    requested = {p.split(':')[0] for p in targets}
    extra = names - requested
    conflicts = (extra - set(config['allowed_dependents'])) | (names & set(config['protect']))
    if conflicts or requested - names:
        raise ValueError('模拟结果与清单不符，请检查：' + ', '.join(sorted(conflicts | (requested - names))))
    print('包管理器模拟删除 ' + str(len(planned)) + ' 项。')
    if extra:
        print('清单允许的连带项：' + ', '.join(sorted(extra)))


def main():
    parser = argparse.ArgumentParser(description='查看个人桌面重装计划')
    parser.add_argument('edition', choices=['debian13', 'arch'])
    parser.add_argument('--installed', action='store_true', help='在对应系统上比对已安装包并模拟清理')
    args = parser.parse_args()
    edition = load_profile(args.edition)
    common = load_profile('common')
    print(edition['name'])
    print('1. 清理默认应用（' + edition['manager'] + '）')
    if args.installed:
        if distro_id() != args.edition:
            raise ValueError('--installed 需要在所选发行版上运行。')
        preview_cleanup(edition)
    else:
        print('候选清单：profiles/' + args.edition + '.json')
    if edition.get('localization'):
        language = edition['localization']
        print('中文环境：' + language['language'] + '，' + language['input_framework']
              + ' + ' + language['input_method'])
        print('语言与输入依赖：' + ', '.join(language['packages']))
    for label, key in [('开发环境','environment'), ('应用','apps'),
                       ('GNOME 外观','appearance'), ('GNOME 扩展','extensions')]:
        print(label + '：' + '、'.join(common[key]))
        for item in common[key]:
            if item in common['projects']:
                print('   ' + '、'.join(common['projects'][item]['includes']))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc))
