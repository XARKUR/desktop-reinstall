#!/usr/bin/env python3
"""Modular GNOME setup: Debian 13 workflow, Arch cleanup and locale. Default: read-only plan."""
import argparse
import ast
import datetime
import fcntl
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import subprocess
import sys
import tempfile

from sources import fetch_project, fetch_extension

ROOT = Path(__file__).resolve().parent
MODULES = {
    'cleanup': '清理默认应用',
    'locale': '简体中文、字体和智能拼音',
    'tools': '日历、时钟与 GNOME 基础工具',
    'docker': 'Docker Engine、Compose、Buildx',
    'fnm': 'fnm 管理器（不预装 Node.js）',
    'uv': 'uv / uvx',
    'appearance': 'Orchis、Tela、Breeze 与 User Themes',
    'weather': 'Gnome Weather 与日历天气卡片',
    'lunar': 'Gnome Lunar',
    'monitor': 'Gnome Monitor',
    'dock': 'Dash to Dock 与边缘触发设置',
    'appindicator': 'AppIndicator 托盘扩展',
}
GROUPS = {'environment': ['docker', 'fnm', 'uv'], 'apps': ['tools', 'weather'],
          'extensions': ['lunar', 'monitor', 'dock', 'appindicator']}
PROJECTS = {'appearance': 'gnome-appearance', 'weather': 'Gnome Weather',
            'lunar': 'Gnome Lunar', 'monitor': 'Gnome Monitor'}
GUI_MODULES = {'tools', 'locale', 'appearance', 'weather', 'lunar', 'monitor', 'dock', 'appindicator'}
TOOL_PACKAGES = ['gnome-calendar', 'gnome-clocks', 'gnome-tweaks', 'gnome-shell-extension-prefs',
                 'nautilus', 'gnome-terminal', 'gnome-calculator', 'gnome-text-editor',
                 'gnome-system-monitor', 'gnome-disk-utility', 'file-roller', 'loupe', 'evince']
PROJECT_PACKAGES = {
    'appearance': ['gjs', 'libglib2.0-bin', 'libgtk-3-bin', 'sassc', 'gtk2-engines-murrine', 'gnome-themes-extra'],
    'weather': ['locales', 'fonts-noto-cjk', 'fonts-noto-color-emoji', 'gjs', 'libglib2.0-bin', 'gir1.2-gtk-4.0', 'gir1.2-adw-1',
                'gir1.2-gweather-4.0', 'gir1.2-soup-3.0', 'gir1.2-geoclue-2.0'],
    'lunar': ['gjs', 'libglib2.0-bin'],
    'monitor': ['gjs', 'libglib2.0-bin', 'gnome-system-monitor', 'pciutils', 'pci.ids'],
}
ARCH_PROJECT_PACKAGES = {
    'appearance': ['gjs', 'glib2', 'gtk3', 'sassc', 'gnome-themes-extra'],
    'weather': ['glibc', 'noto-fonts-cjk', 'noto-fonts-emoji', 'gjs', 'glib2', 'gtk4',
                'libadwaita', 'libgweather-4', 'libsoup3', 'geoclue'],
    'lunar': ['gjs', 'glib2'],
    'monitor': ['gjs', 'glib2', 'gnome-system-monitor', 'pciutils', 'hwdata'],
}


def load(path):
    return json.loads(Path(path).read_text())


def defaults(common):
    selected = {'cleanup', 'locale', 'tools'}
    for module, name in [('docker', 'Docker'), ('fnm', 'fnm（管理 Node.js）'), ('uv', 'uv（管理 Python）')]:
        if name in common['environment']:
            selected.add(module)
    if 'gnome-appearance' in common['appearance']:
        selected.add('appearance')
    if 'Gnome Weather' in common['apps']:
        selected.add('weather')
    for module, name in [('lunar', 'Gnome Lunar'), ('monitor', 'Gnome Monitor'),
                         ('dock', 'Dash to Dock'), ('appindicator', 'AppIndicator and KStatusNotifierItem Support')]:
        if name in common['extensions']:
            selected.add(module)
    return selected


def expand(value):
    result = set()
    for name in value.split(','):
        name = name.strip()
        if name in GROUPS:
            result.update(GROUPS[name])
        elif name in MODULES:
            result.add(name)
        else:
            raise ValueError('未知模块：' + name)
    return result


def select_modules(common, only=None, skip=None):
    selected = expand(only) if only is not None else defaults(common)
    if skip is not None:
        selected -= expand(skip)
    if not selected:
        raise ValueError('没有选择任何模块。')
    return [name for name in MODULES if name in selected]


class Installer:
    def __init__(self, edition, common, selected, profile):
        self.edition, self.common, self.selected, self.profile = edition, common, selected, Path(profile).resolve()
        self.environment = os.environ.copy()
        self.prepared = {}
        self.apt_updated = False
        self.record = {'modules': selected, 'completed': [], 'commands': []}
        self.settings_before = {}

    def preflight(self):
        if os.geteuid() == 0:
            raise ValueError('请以 GNOME 桌面用户运行整个入口，需要时脚本会调用 sudo。')
        release = platform.freedesktop_os_release()
        arch = self.edition.get('os_id') == 'arch'
        if arch:
            if release.get('ID') != 'arch' or platform.machine() != 'x86_64':
                raise ValueError('Arch 配置需要在 Arch Linux x86_64 上执行。')
        elif (release.get('ID') != 'debian' or release.get('VERSION_ID') != '13'
              or platform.machine() != 'x86_64' or self.edition.get('os_id') != 'debian'
              or self.edition.get('version_id') != '13'):
            raise ValueError('实际执行适用于 Debian 13 或 Arch Linux x86_64。')
        for name in (['sudo', 'pacman'] if arch else ['sudo', 'apt-get', 'dpkg-query']):
            if not shutil.which(name):
                raise ValueError('缺少系统命令：' + name)
        if set(self.selected) & GUI_MODULES:
            bus = Path('/run/user') / str(os.getuid()) / 'bus'
            if not self.environment.get('DBUS_SESSION_BUS_ADDRESS'):
                if not bus.exists():
                    raise ValueError('所选桌面模块需要已经登录的 GNOME 会话。')
                self.environment['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=' + str(bus)
                self.environment.setdefault('XDG_RUNTIME_DIR', str(bus.parent))
            version = self.read(['gnome-shell', '--version'])
            if not re.search(r'GNOME Shell\s+(48|51)(?:\.|\s|$)', version):
                raise ValueError('桌面项目已验证的 Shell 主版本为 48 和 51：' + version.strip())
            if 'appearance' in self.selected:
                disabled = self.read(['gsettings', 'get', 'org.gnome.shell', 'disable-user-extensions']).strip()
                if disabled == 'true':
                    raise ValueError('当前 GNOME 全局禁用了用户扩展，请先在“扩展”应用启用，才能应用 Shell 主题。')
        lock = load(ROOT / 'environment/sources.lock.json')
        for name in ['fnm', 'uv']:
            if name in self.selected and self.common['environment_settings'][name]['version'] != lock[name]['version']:
                raise ValueError(name + ' 版本与 sources.lock.json 不一致，请同时更新来源与校验值。')
        if 'docker' in self.selected:
            config = self.common['environment_settings']['docker']
            source = config.get('arch_source') if arch else config['source']
            if source != ('official-repository' if arch else 'official-stable') or not all(isinstance(config[key], bool)
                    for key in ['add_user_to_group', 'compose', 'buildx']):
                raise ValueError('Docker 预设需要对应系统的官方来源及布尔类型的组件开关。')

    def read(self, args):
        return subprocess.check_output(list(map(str, args)), text=True, env=self.environment)

    def run(self, args):
        argv = list(map(str, args))
        self.record['commands'].append(argv)
        subprocess.run(argv, check=True, env=self.environment)

    def save(self):
        (self.state / 'run.json').write_text(json.dumps(self.record, ensure_ascii=False, indent=2) + '\n')
        (self.state / 'settings-before.json').write_text(json.dumps(self.settings_before, ensure_ascii=False, indent=2) + '\n')

    def ensure_packages(self, packages):
        packages = sorted(set(packages))
        if not all(re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', name) for name in packages):
            raise ValueError('包名无效。')
        if not packages:
            return
        if self.edition.get('os_id') == 'arch':
            installed = set(self.read(['pacman', '-Qq']).splitlines())
            missing = [name for name in packages if name not in installed]
            if missing:
                # Use the existing repository snapshot; never refresh it alone with -Sy.
                self.read(['pacman', '-Si', '--', *missing])
                self.run(['sudo', 'pacman', '-S', '--needed', '--noconfirm', '--', *missing])
            return
        query = subprocess.run(['dpkg-query', '-W', '-f=${binary:Package} ${db:Status-Abbrev}\n', *packages],
                               capture_output=True, text=True, env=self.environment)
        installed = {line.split()[0].split(':')[0] for line in query.stdout.splitlines()
                     if line.split()[1:2] == ['ii']}
        missing = [name for name in packages if name not in installed]
        if missing:
            if not self.apt_updated:
                self.run(['sudo', 'apt-get', 'update'])
                self.apt_updated = True
            self.run(['sudo', 'apt-get', 'install', '-y', '--no-install-recommends', *missing])

    def setting(self, schema, key, value, schema_dir=None):
        identity = schema + ' ' + key
        args = ['gsettings']
        if schema_dir is not None:
            args += ['--schemadir', str(schema_dir)]
        if identity not in self.settings_before:
            self.settings_before[identity] = self.read(args + ['get', schema, key]).strip()
            self.save()
        self.run(args + ['set', schema, key, value])

    def prepare(self, temp):
        cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'desktop-reinstall'
        for module in self.selected:
            if module not in PROJECTS:
                continue
            name = PROJECTS[module]
            print('准备固定版本项目：' + name, flush=True)
            project = self.common['projects'][name]
            source = fetch_project(project, Path(temp) / module, cache)
            entry = 'appearance.py' if module == 'appearance' else 'project.py'
            if not (source / entry).is_file():
                raise ValueError('项目入口缺失：' + name)
            self.prepared[module] = source
        if 'dock' in self.selected and self.edition.get('os_id') == 'arch':
            config = self.common['system_extensions']['Dash to Dock']
            major = re.search(r'GNOME Shell\s+(\d+)', self.read(['gnome-shell', '--version'])).group(1)
            self.prepared['dock'] = fetch_extension(config['arch'], config['uuid'], major,
                Path(temp) / 'dock', cache)

    def locale(self):
        config = self.edition['localization']
        self.ensure_packages(config['packages'])
        self.run(['sudo', sys.executable, ROOT / 'modules/locales-root.py',
                  '--profile', self.profile, '--user', pwd.getpwuid(os.getuid()).pw_name])
        self.setting('org.gnome.system.locale', 'region', repr(config['language']))
        schema = 'org.gnome.desktop.input-sources'
        before = self.read(['gsettings', 'get', schema, 'sources']).strip()
        values = ast.literal_eval(before.replace('@a(ss) ', ''))
        for source in config['input_sources']:
            item = tuple(source)
            if item not in values:
                values.append(item)
        self.setting(schema, 'sources', repr(values))

    def extension(self, module):
        name = 'Dash to Dock' if module == 'dock' else 'AppIndicator and KStatusNotifierItem Support'
        config = self.common['system_extensions'][name]
        edition = 'arch' if self.edition.get('os_id') == 'arch' else 'debian13'
        uuid = config['uuid']
        if isinstance(uuid, dict):
            uuid = uuid[edition]
        schema_dir = None
        if isinstance(config[edition], dict):
            source = self.prepared[module]
            self.run(['glib-compile-schemas', '--strict', source / 'schemas'])
            data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
            target = data / 'gnome-shell/extensions' / uuid
            if target.is_symlink() or (target.exists() and load(target / 'metadata.json').get('uuid') != uuid):
                raise ValueError('已有用户扩展目录不属于所选扩展：' + uuid)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                backup = self.state / 'extensions' / uuid
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(target, backup, symlinks=True)
            with tempfile.TemporaryDirectory(prefix='.desktop-extension-', dir=target.parent) as temp:
                staged, previous = Path(temp) / 'new', Path(temp) / 'previous'
                shutil.copytree(source, staged)
                if target.exists(): target.rename(previous)
                try:
                    staged.rename(target)
                except BaseException:
                    if previous.exists(): previous.rename(target)
                    raise
            metadata = target / 'metadata.json'
            schema_dir = target / 'schemas'
        else:
            self.ensure_packages([config[edition]])
            metadata = Path('/usr/share/gnome-shell/extensions') / uuid / 'metadata.json'
        info = load(metadata)
        version = self.read(['gnome-shell', '--version'])
        major = re.search(r'GNOME Shell\s+(\d+)', version).group(1)
        if major not in info['shell-version'] or uuid != info['uuid']:
            raise ValueError('发行版扩展与当前 Shell 不兼容：' + name)
        schema = 'org.gnome.shell'
        enabled = ast.literal_eval(self.read(['gsettings', 'get', schema, 'enabled-extensions']).replace('@as ', ''))
        disabled = ast.literal_eval(self.read(['gsettings', 'get', schema, 'disabled-extensions']).replace('@as ', ''))
        if uuid not in enabled:
            self.setting(schema, 'enabled-extensions', repr([*enabled, uuid]))
        if uuid in disabled:
            self.setting(schema, 'disabled-extensions', repr([item for item in disabled if item != uuid]))
        for key, value in config.get('settings', {}).items():
            args = ['org.gnome.shell.extensions.dash-to-dock', key,
                    str(value).lower() if isinstance(value, bool) else repr(value)]
            if schema_dir is not None:
                self.setting(*args, schema_dir=schema_dir)
            else:
                self.setting(*args)

    def configure_project(self, module, first_install):
        config = self.common['projects'][PROJECTS[module]]
        if not config.get('uuid'):
            return
        data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
        schema_dir = data / 'gnome-shell/extensions' / config['uuid'] / 'schemas'
        if first_install:
            for key, value in config.get('initial_settings', {}).items():
                self.setting(config['schema'], key, value, schema_dir=schema_dir)
        if module == 'monitor' and self.edition.get('monitor_auto_gpu'):
            current = ast.literal_eval(self.read(['gsettings', '--schemadir', schema_dir,
                'get', config['schema'], 'gpudeviceslist']).replace('@as ', ''))
            if not current:
                detected = json.loads(self.read(['gjs', '-m', ROOT / 'modules/detect-monitor-gpus.mjs', schema_dir.parent]))
                if detected['devices']:
                    for key, values in [('gpudeviceslist', detected['devices']),
                                        ('thermalgputemperaturedeviceslist', detected['thermal'])]:
                        self.setting(config['schema'], key, repr([json.dumps(item) for item in values]), schema_dir=schema_dir)
                    self.setting(config['schema'], 'gpustatus', 'true', schema_dir=schema_dir)
                    self.setting(config['schema'], 'thermalgputemperaturestatus', 'true' if detected['thermal'] else 'false', schema_dir=schema_dir)

    def execute(self, module):
        if module == 'cleanup':
            script = 'cleanup-arch.py' if self.edition.get('os_id') == 'arch' else 'cleanup.py'
            self.run(['sudo', sys.executable, ROOT / 'modules' / script, '--profile', self.profile, '--apply'])
        elif module == 'locale':
            self.locale()
        elif module == 'tools':
            self.ensure_packages(self.edition.get('tool_packages', TOOL_PACKAGES))
            for schema, values in self.edition.get('desktop_settings', {}).items():
                for key, value in values.items():
                    self.setting(schema, key, value)
        elif module == 'docker':
            config = self.common['environment_settings']['docker']
            edition = 'arch' if self.edition.get('os_id') == 'arch' else 'debian'
            self.run(['sudo', 'bash', ROOT / 'environment' / ('install-docker-' + edition + '.sh'), pwd.getpwuid(os.getuid()).pw_name,
                      str(config['add_user_to_group']).lower(), str(config['compose']).lower(), str(config['buildx']).lower()])
        elif module in ('fnm', 'uv'):
            self.ensure_packages(['curl', 'ca-certificates'])
            self.run([sys.executable, ROOT / 'environment/install-user-tools.py', '--only', module])
        elif module in PROJECTS:
            packages = ARCH_PROJECT_PACKAGES if self.edition.get('os_id') == 'arch' else PROJECT_PACKAGES
            self.ensure_packages(packages[module])
            if module == 'weather' and 'locale' not in self.selected:
                available = self.read(['locale', '-a']).lower().replace('-', '').splitlines()
                if 'zh_cn.utf8' not in available:
                    self.run(['sudo', sys.executable, ROOT / 'modules/locales-root.py',
                              '--profile', self.profile, '--user', pwd.getpwuid(os.getuid()).pw_name,
                              '--generate-only'])
            source = self.prepared[module]
            entry = 'appearance.py' if module == 'appearance' else 'project.py'
            argv = [sys.executable, source / entry, 'setup']
            if module == 'appearance':
                argv.append('--skip-deps')
            config = self.common['projects'][PROJECTS[module]]
            data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
            first_install = not (data / 'gnome-shell/extensions' / config.get('uuid', 'not-an-extension')).exists()
            self.run(argv)
            self.configure_project(module, first_install)
        else:
            self.extension(module)

    def apply(self):
        self.preflight()
        base = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'desktop-reinstall'
        base.mkdir(parents=True, exist_ok=True)
        with (base / 'install.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('另一个安装流程正在运行。')
            self.state = base / ('run-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            self.state.mkdir(mode=0o700)
            self.save()
            try:
                with tempfile.TemporaryDirectory(prefix='desktop-reinstall-') as temp:
                    # Resolve all selected source archives before removing/installing packages.
                    self.prepare(temp)
                    for module in self.selected:
                        self.record['current'] = module
                        self.save()
                        print('\n执行：' + MODULES[module], flush=True)
                        self.execute(module)
                        self.record['completed'].append(module)
                        self.save()
                self.record['status'] = 'READY'
            except BaseException as error:
                self.record['status'] = 'FAILED'
                self.record['error'] = str(error)
                self.save()
                print('执行记录：' + str(self.state), file=sys.stderr)
                raise
            self.save()
            print('READY：所选模块已完成。记录：' + str(self.state))
            if set(self.selected) & (GUI_MODULES | {'docker'}):
                print('请保存工作后注销并重新登录，加载语言、扩展和新增的组权限。')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--plan', action='store_true', help='仅查看计划（默认）')
    modes.add_argument('--apply', action='store_true', help='实际执行选择的模块')
    modes.add_argument('--check', action='store_true', help='只检查目标系统与桌面会话')
    modes.add_argument('--list', action='store_true', help='列出模块')
    parser.add_argument('--only', help='逗号分隔的模块或分组')
    parser.add_argument('--skip', help='从本次选择中排除模块或分组')
    parser.add_argument('--profile', type=Path, help='配置文件；默认按当前系统选择 Debian 13 / Arch')
    parser.add_argument('--common', type=Path, default=ROOT / 'profiles/common.json')
    args = parser.parse_args(argv)
    if args.list:
        for name, title in MODULES.items():
            print(name.ljust(14) + title)
        print('分组：environment=docker,fnm,uv；apps=tools,weather；extensions=lunar,monitor,dock,appindicator')
        return 0
    profile = args.profile
    if profile is None:
        name = 'arch' if platform.freedesktop_os_release().get('ID') == 'arch' else 'debian13'
        profile = ROOT / 'profiles' / (name + '.json')
    edition, common = load(profile), load(args.common)
    selected = select_modules(common, args.only, args.skip)
    for module in selected:
        print(module.ljust(14) + MODULES[module])
        if module in PROJECTS:
            project = common['projects'][PROJECTS[module]]
            print('  ' + project['repository'] + ' @ ' + project['commit'][:12])
    installer = Installer(edition, common, selected, profile)
    if args.apply:
        installer.apply()
    elif args.check:
        installer.preflight()
        print('检查通过，未执行安装。')
    else:
        print('仅预览。实际安装请添加 --apply。')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError, SyntaxError, KeyError, TypeError) as error:
        print('停止：' + str(error), file=sys.stderr)
        sys.exit(1)
