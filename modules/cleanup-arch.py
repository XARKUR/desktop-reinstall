#!/usr/bin/env python3
"""Remove reviewed Arch desktop applications; default is a print-only transaction."""
import argparse
import contextlib
import datetime
import fcntl
import json
import os
from pathlib import Path
import platform
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, LC_ALL='C')
REQUIRED = {'gnome-calendar', 'gnome-clocks', 'gdm', 'gnome-shell', 'gnome-session',
            'gnome-control-center', 'gnome-keyring', 'networkmanager', 'openssh',
            'sudo', 'pacman', 'glibc', 'systemd', 'python'}


def read(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, env=ENV)


def installed():
    return dict(row.split(' ', 1) for row in read(['pacman', '-Q']).splitlines())


def validate_profile(data):
    if data.get('os_id') != 'arch' or data.get('manager') != 'pacman':
        raise RuntimeError('需要 Arch / pacman 清理配置。')
    config = data['cleanup']
    if config.get('remove_prefix') or config.get('allowed_dependents'):
        raise RuntimeError('Arch 实际清理只接受逐个确认的包名，不启用前缀或连带删除。')
    for key in ('remove_exact', 'protect'):
        if not isinstance(config[key], list) or not all(isinstance(name, str) and
                re.fullmatch(r'[a-z0-9][a-z0-9@._+\-]*', name) for name in config[key]):
            raise RuntimeError('清理配置包含无效包名。')
    protected = set(config['protect']) | REQUIRED
    if set(config['remove_exact']) & protected:
        raise RuntimeError('清理候选与受保护组件冲突。')
    return config, protected


def removal_plan(output, requested, protected):
    names = output.splitlines()
    if len(names) != len(set(names)) or set(names) != set(requested) or set(names) & protected:
        raise RuntimeError('模拟结果包含额外删除、缺少目标或涉及受保护组件，停止。')
    return names


def verify_after(before, after, requested, protected):
    removed = set(before) - set(after)
    if removed != set(requested):
        raise RuntimeError('实际移除的软件包与已审核目标不一致。')
    if (set(before) & protected) - set(after):
        raise RuntimeError('受保护软件包缺失。')
    if any(after.get(name) != version for name, version in before.items() if name not in removed):
        raise RuntimeError('清理期间其他软件包版本发生变化，请检查并行包管理操作。')
    if set(after) - set(before):
        raise RuntimeError('清理期间出现额外安装，请检查并行包管理操作。')
    return sorted(removed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--profile', type=Path, default=ROOT / 'profiles/arch.json')
    args = parser.parse_args(argv)
    if platform.freedesktop_os_release().get('ID') != 'arch':
        raise RuntimeError('此清理入口仅适用于 Arch Linux。')
    if args.apply and os.geteuid() != 0:
        raise RuntimeError('实际清理需要管理员权限，请通过主安装入口运行。')
    config, protected = validate_profile(json.loads(args.profile.read_text()))
    with contextlib.ExitStack() as stack:
        if args.apply:
            lock = stack.enter_context(Path('/run/lock/desktop-reinstall-arch-cleanup.lock').open('a'))
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('另一个 Arch 清理流程正在运行。')
        before = installed()
        requested = sorted(set(before) & set(config['remove_exact']))
        if not requested:
            print('READY：清单中的附带应用已经移除，未执行卸载。')
            return
        simulation = read(['pacman', '-Rp', '--print-format', '%n', '--', *requested])
        removal_plan(simulation, requested, protected)
        print('模拟删除 ' + str(len(requested)) + ' 项：' + ' '.join(requested), flush=True)
        if not args.apply:
            print('仅模拟；日历、时钟与桌面组件保留。')
            return
        # Recheck package state before handing the exact reviewed targets to pacman.
        if installed() != before:
            raise RuntimeError('模拟后软件包状态已变化，请重新执行。')
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        report = Path('/var/log/desktop-reinstall') / ('arch-cleanup-' + stamp)
        report.mkdir(parents=True, mode=0o700)
        (report / 'profile.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
        (report / 'installed-before.json').write_text(json.dumps(before, indent=2) + '\n')
        (report / 'explicit-before.txt').write_text(read(['pacman', '-Qqe']))
        (report / 'simulation.txt').write_text(simulation)
        (report / 'removed-packages.json').write_text(json.dumps({name: before[name] for name in requested}, indent=2) + '\n')
        result = {'status': 'RUNNING', 'requested': requested}
        print('清理记录：' + str(report), flush=True)
        try:
            # Plain -R preserves dependencies and saved configuration files. Never -s/-c/-d/-n.
            with (report / 'apply.log').open('w') as log:
                subprocess.run(['pacman', '-R', '--noconfirm', '--', *requested], check=True,
                               stdout=log, stderr=subprocess.STDOUT, env=ENV)
            after = installed()
            (report / 'installed-after.json').write_text(json.dumps(after, indent=2) + '\n')
            removed = verify_after(before, after, requested, protected)
            audit = read(['pacman', '-Dk'])
            (report / 'audit.txt').write_text(audit)
            result = {'status': 'READY', 'removed': removed, 'protected_packages_preserved': True}
        except BaseException as error:
            result['status'] = 'FAILED'
            result['error'] = str(error)
            raise
        finally:
            (report / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print('READY：已移除 ' + str(len(removed)) + ' 项；日历、时钟和其他保护组件均保留。')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
