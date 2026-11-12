"""Download pinned GitHub source archives and safely stage them for one run."""
import hashlib
import io
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import time
import urllib.request


def fetch_project(project, destination, cache):
    repository, commit = project['repository'], project['commit']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('项目来源必须是 GitHub 仓库和完整提交编号。')
    cache.mkdir(parents=True, exist_ok=True)
    name = repository.replace('/', '-') + '-' + commit
    archive = cache / (name + '.tar.gz')
    checksum = cache / (name + '.sha256')
    if archive.exists() and checksum.exists():
        data = archive.read_bytes()
        valid = hashlib.sha256(data).hexdigest() == checksum.read_text().strip()
    else:
        valid = False
    if not valid:
        url = 'https://codeload.github.com/' + repository + '/tar.gz/' + commit
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'desktop-reinstall'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    data = response.read(32 * 1024 * 1024 + 1)
                if len(data) > 32 * 1024 * 1024:
                    raise ValueError('项目下载包超过大小限制。')
                break
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(2)
        partial = archive.with_suffix('.partial')
        partial.write_bytes(data)
        partial.replace(archive)
        checksum.write_text(hashlib.sha256(data).hexdigest() + '\n')
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as source:
        total = 0
        for index, member in enumerate(source):
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError('项目归档包含不支持的路径或链接。')
            total += member.size
            if index > 100000 or total > 128 * 1024 * 1024:
                raise ValueError('项目解压大小超过限制。')
            target = destination.joinpath(*path.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as stream, target.open('xb') as output:
                    shutil.copyfileobj(stream, output)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
    roots = list(destination.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise ValueError('项目归档目录结构无效。')
    return roots[0]


def fetch_extension(config, uuid, major, destination, cache):
    """Stage one checksum-pinned EGO extension and validate its metadata before mutation."""
    import json
    import stat
    import zipfile
    from urllib.parse import urlsplit
    url, digest = config['url'], config['sha256']
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'extensions.gnome.org' or not parsed.path.startswith('/download-extension/'):
        raise ValueError('用户扩展必须来自 GNOME 官方扩展站。')
    if not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('扩展缺少固定 SHA256。')
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / (digest + '.zip')
    data = archive.read_bytes() if archive.exists() else b''
    if hashlib.sha256(data).hexdigest() != digest:
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=45) as response:
                    data = response.read(16 * 1024 * 1024 + 1)
                break
            except OSError:
                if attempt == 2: raise
                time.sleep(2)
        if len(data) > 16 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('扩展下载大小或校验值不符。')
        archive.write_bytes(data)
    destination.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        members = source.infolist()
        if len(members) > 10000 or sum(item.file_size for item in members) > 32 * 1024 * 1024:
            raise ValueError('扩展解压大小超过限制。')
        for member in members:
            path = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if path.is_absolute() or '..' in path.parts or stat.S_ISLNK(mode):
                raise ValueError('扩展包含不支持的路径或符号链接。')
            target = destination.joinpath(*path.parts)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(member) as stream, target.open('xb') as output:
                    shutil.copyfileobj(stream, output)
                target.chmod(0o644)
    meta = json.loads((destination / 'metadata.json').read_text())
    if meta['uuid'] != uuid or str(major) not in meta['shell-version'] or meta['version'] != config['version']:
        raise ValueError('扩展身份、版本或 GNOME 兼容性不符。')
    return destination
