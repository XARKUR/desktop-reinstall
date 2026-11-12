#!/usr/bin/env python3
"""Remove selected Debian 13 applications. Default: simulation only."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
ENV = dict(os.environ, LC_ALL='C', DEBIAN_FRONTEND='noninteractive')


def run(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, env=ENV)


def installed():
    result = {}
    for row in run(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${db:Status-Abbrev}\n']).splitlines():
        name, version, status = row.split('\t')
        if status.startswith('ii'):
            result[name] = version
    return result


def base(name):
    return name.split(':')[0]


def selection(packages, profile):
    return sorted(name for name in packages if base(name) in profile['remove_exact'] or
                  any(base(name).startswith(prefix) for prefix in profile['remove_prefix']))


def removal_plan(output, requested, profile):
    planned = re.findall(r'^(?:Remv|Purg) (\S+)', output, re.M)
    if re.search(r'^Inst ', output, re.M):
        raise RuntimeError('Refusing a removal plan that installs replacement packages.')
    allowed = set(map(base, requested)) | set(profile['allowed_dependents'])
    protected = set(profile['protect'])
    blocked = [name for name in planned if base(name) in protected or base(name) not in allowed]
    if blocked:
        raise RuntimeError('Unreviewed dependent or protected package in removal plan: ' + ', '.join(blocked))
    return planned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Actually remove packages; requires administrator privileges')
    parser.add_argument('--profile', type=Path, default=ROOT.parent / 'profiles/debian13.json')
    args = parser.parse_args()
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if release.get('ID', '').strip('"') != 'debian' or release.get('VERSION_ID', '').strip('"') != '13':
        raise RuntimeError('This profile supports Debian 13 only.')
    if args.apply and os.geteuid() != 0:
        raise RuntimeError('Actual removal requires administrator privileges. Use sudo python3 cleanup.py --apply.')
    # Only one privileged cleanup may plan and mutate package state at a time.
    lock = None
    if args.apply:
        lock = Path('/run/lock/debian13-desktop-cleanup.lock').open('a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another desktop cleanup is already running.')
    data = json.loads(args.profile.read_text())
    profile = data.get('cleanup', data)
    before = installed()
    requested = selection(before, profile)
    if not requested:
        print('READY: selected default applications are already absent.')
        return
    simulation = run(['apt-get', '-s', '-o', 'APT::Get::AutomaticRemove=false', 'remove', *requested])
    planned = removal_plan(simulation, requested, profile)
    print('Planned removals (' + str(len(planned)) + '): ' + ' '.join(planned), flush=True)
    if not args.apply:
        print('Simulation only. Protected desktop, network, SSH and application runtimes remain installed.')
        return
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    report = Path('/var/log/debian13-desktop') / ('cleanup-' + stamp)
    report.mkdir(parents=True)
    (report / 'profile.json').write_text(json.dumps(profile, indent=2) + '\n')
    (report / 'installed-before.json').write_text(json.dumps(before, indent=2) + '\n')
    (report / 'manual-before.txt').write_text(run(['apt-mark', 'showmanual']))
    (report / 'auto-before.txt').write_text(run(['apt-mark', 'showauto']))
    (report / 'simulation.txt').write_text(simulation)
    (report / 'removed-packages.json').write_text(json.dumps({name: before[name] for name in planned}, indent=2) + '\n')
    # Runtime libraries used by user-installed applications are invisible to APT.
    # Preserve the reviewed desktop/runtime roots for future dependency cleanup.
    keep = sorted(name for name in before if base(name) in profile['protect'])
    with (report / 'apply.log').open('w') as log:
        subprocess.run(['apt-mark', 'manual', *keep], check=True, stdout=log, stderr=subprocess.STDOUT, env=ENV)
        subprocess.run(['apt-get', '-y', '-o', 'APT::Get::AutomaticRemove=false', 'remove', *requested],
                       check=True, stdout=log, stderr=subprocess.STDOUT, env=ENV)
        subprocess.run(['apt-get', 'check'], check=True, stdout=log, stderr=subprocess.STDOUT, env=ENV)
    after = installed()
    protected_before = {name for name in before if base(name) in profile['protect']}
    assert protected_before <= set(after), 'A protected package is missing after removal.'
    assert not selection(after, profile), 'Some selected applications remain installed.'
    audit = run(['dpkg', '--audit'])
    if audit.strip():
        raise RuntimeError('Package audit requires attention: ' + audit)
    (report / 'result.json').write_text(json.dumps({'status': 'READY', 'removed': sorted(set(before) - set(after)),
                                                  'protected_packages_preserved': True}, indent=2) + '\n')
    print('READY: ' + str(len(set(before) - set(after))) + ' packages removed. Report: ' + str(report))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
