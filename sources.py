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
