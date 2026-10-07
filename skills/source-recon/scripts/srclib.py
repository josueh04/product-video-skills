"""Helpers shared by fetch_sources.py and changed_since.py.

Git calls, ref resolution, read-only exports and tree hashes. Nothing here writes into a
user's repository: local repos are only read (rev-parse, archive, diff, log).
"""
import datetime
import hashlib
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CACHE_DIR = ".git-cache"  # sources/.git-cache/<role>.git holds bare clones of URL sources
SKIP_COPY = {".git", "node_modules", ".DS_Store", "dist", "build", ".next", ".angular", "coverage"}


class SourceError(Exception):
    pass


def now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def git(args: List[str], cwd: Optional[Path] = None, git_dir: Optional[Path] = None,
        check: bool = True) -> str:
    cmd = ["git"]
    if git_dir is not None:
        cmd += ["--git-dir", str(git_dir)]
    elif cwd is not None:
        cmd += ["-C", str(cwd)]
    cmd += args
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    if check and p.returncode != 0:
        raise SourceError(f"git {' '.join(args)} failed: {p.stderr.strip()[:400]}")
    return p.stdout.strip() if p.returncode == 0 else ""


def is_git_repo(path: Path) -> bool:
    if not path.exists():
        return False
    p = subprocess.run(["git", "-C", str(path), "rev-parse", "--git-dir"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode == 0


def git_toplevel(path: Path) -> Optional[Path]:
    """The root of the git work tree that holds `path`, or None when it is in none."""
    if not path.exists():
        return None
    p = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return Path(p.stdout.strip()).resolve() if p.returncode == 0 and p.stdout.strip() else None


def is_git_root(path: Path) -> bool:
    """True only for the root of a git work tree (or a bare repo).

    A folder inside some other repo (the product's own repo, the workbench, a monorepo
    subfolder) is not a git source: `git archive` from there exports a commit of the outer
    repo, which fails for ignored folders and moves with every unrelated commit.
    """
    top = git_toplevel(path)
    if top is not None:
        return top == Path(path).resolve()
    return is_git_repo(path)


def rev(repo: Path, ref: str) -> Optional[str]:
    out = git(["rev-parse", "--verify", "--quiet", ref + "^{commit}"], cwd=repo, check=False)
    return out or None


def is_ancestor(repo: Path, a: str, b: str) -> bool:
    p = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", a, b],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode == 0


def commit_date(repo: Path, sha: str) -> str:
    return git(["log", "-1", "--format=%cs", sha], cwd=repo, check=False)


def resolve_local_ref(repo: Path, branch: str) -> Tuple[str, str, List[str]]:
    """Pick the newest of <branch> and origin/<branch>. Returns (ref, sha, warnings).

    A local checkout that is behind its remote-tracking branch is the most expensive mistake
    this guards against: the UI gets rebuilt from code that is no longer in production.
    """
    warnings: List[str] = []
    if not branch:
        sha = rev(repo, "HEAD")
        if not sha:
            raise SourceError(f"{repo}: no HEAD commit")
        warnings.append("no branch in product.yaml: exported HEAD; set the production branch")
        return "HEAD", sha, warnings
    if branch.startswith("origin/") or branch.startswith("refs/"):
        sha = rev(repo, branch)
        if not sha:
            raise SourceError(f"{repo}: ref {branch} not found")
        return branch, sha, warnings
    local = rev(repo, "refs/heads/" + branch)
    remote = rev(repo, "refs/remotes/origin/" + branch)
    if not local and not remote:
        tag = rev(repo, branch)
        if tag:
            return branch, tag, warnings
        raise SourceError(f"{repo}: branch {branch} not found (local or origin/{branch})")
    if local and not remote:
        return branch, local, warnings
    if remote and not local:
        return "origin/" + branch, remote, warnings
    if local == remote:
        return branch, local, warnings
    if is_ancestor(repo, local, remote):
        n = git(["rev-list", "--count", f"{local}..{remote}"], cwd=repo, check=False)
        warnings.append(f"local {branch} is {n} commits behind origin/{branch}: exported origin/{branch}")
        return "origin/" + branch, remote, warnings
    if is_ancestor(repo, remote, local):
        n = git(["rev-list", "--count", f"{remote}..{local}"], cwd=repo, check=False)
        warnings.append(f"local {branch} is {n} commits ahead of origin/{branch} (unpushed?): exported local {branch}")
        return branch, local, warnings
    ld, rd = commit_date(repo, local), commit_date(repo, remote)
    pick = ("origin/" + branch, remote) if rd >= ld else (branch, local)
    warnings.append(f"local {branch} ({ld}) and origin/{branch} ({rd}) have diverged: exported {pick[0]}; confirm which one is in production")
    return pick[0], pick[1], warnings


def fetch_age_days(repo: Path) -> Optional[float]:
    gd = git(["rev-parse", "--absolute-git-dir"], cwd=repo, check=False)
    if not gd:
        return None
    fh = Path(gd) / "FETCH_HEAD"
    if not fh.exists():
        return None
    return (datetime.datetime.now().timestamp() - fh.stat().st_mtime) / 86400.0


def other_worktrees(repo: Path, exported_sha: str) -> List[str]:
    """Worktrees of the same repo whose HEAD contains the exported commit and is newer."""
    out = git(["worktree", "list", "--porcelain"], cwd=repo, check=False)
    hints, path, head = [], None, None
    for line in out.splitlines() + [""]:
        if line.startswith("worktree "):
            path = line[9:]
        elif line.startswith("HEAD "):
            head = line[5:]
        elif not line.strip() and path and head:
            if head != exported_sha and is_ancestor(repo, exported_sha, head):
                hints.append(f"{path} at {head[:7]} ({commit_date(repo, head)}) is newer than the export")
            path, head = None, None
    return hints


def make_writable(path: Path) -> None:
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        os.chmod(root, os.stat(root).st_mode | stat.S_IWUSR)
        for n in dirs + files:
            p = os.path.join(root, n)
            if not os.path.islink(p):
                os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)
    os.chmod(path, os.stat(path).st_mode | stat.S_IWUSR)


def make_read_only(path: Path) -> None:
    """chmod -R a-w, files first and folders last so the walk can finish."""
    mask = ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    for root, dirs, files in os.walk(path, topdown=False):
        for n in files + dirs:
            p = os.path.join(root, n)
            if not os.path.islink(p):
                os.chmod(p, os.stat(p).st_mode & mask)
        os.chmod(root, os.stat(root).st_mode & mask)


def remove_tree(path: Path) -> None:
    if path.exists() or path.is_symlink():
        make_writable(path)
        shutil.rmtree(path)


def export_commit(repo: Optional[Path], sha: str, dest: Path, git_dir: Optional[Path] = None) -> None:
    """git archive <sha> | tar -x -C dest. Reads objects only; the working tree is never touched."""
    dest.mkdir(parents=True, exist_ok=True)
    cmd = ["git"] + (["--git-dir", str(git_dir)] if git_dir else ["-C", str(repo)]) + ["archive", "--format=tar", sha]
    a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    t = subprocess.run(["tar", "-x", "-C", str(dest)], stdin=a.stdout, stderr=subprocess.PIPE)
    a.stdout.close()
    err = a.stderr.read().decode()
    a.wait()
    if a.returncode != 0 or t.returncode != 0:
        raise SourceError(f"export of {sha[:7]} failed: {err.strip()[:300]} {t.stderr.decode().strip()[:200]}")


def tree_hashes(root: Path) -> Dict[str, str]:
    """relative path -> sha256 of content (or of the link target for symlinks)."""
    out: Dict[str, str] = {}
    root = Path(root)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_COPY)
        for n in sorted(files):
            if n in SKIP_COPY:
                continue
            p = Path(dirpath) / n
            rel = p.relative_to(root).as_posix()
            h = hashlib.sha256()
            if p.is_symlink():
                h.update(("link:" + os.readlink(p)).encode())
            else:
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 16), b""):
                        h.update(chunk)
            out[rel] = h.hexdigest()
    return out


def tree_sha256(root: Path) -> str:
    h = hashlib.sha256()
    for rel, digest in sorted(tree_hashes(root).items()):
        h.update(f"{rel}\0{digest}\n".encode())
    return h.hexdigest()


def copy_tree(src: Path, dest: Path) -> None:
    shutil.copytree(src, dest, symlinks=True, ignore=shutil.ignore_patterns(*SKIP_COPY))


def cache_git_dir(product: Path, role: str) -> Path:
    return product / "sources" / CACHE_DIR / f"{role}.git"


def url_clone_or_fetch(url: str, branch: str, gd: Path, want_sha: Optional[str] = None) -> str:
    """Shallow bare clone (or fetch) of <branch> into gd. Returns the branch head sha."""
    ref = branch or "HEAD"
    if not gd.exists():
        gd.parent.mkdir(parents=True, exist_ok=True)
        args = ["clone", "--bare", "--depth", "1", "--single-branch"]
        if branch:
            args += ["--branch", branch]
        p = subprocess.run(["git"] + args + [url, str(gd)], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        if p.returncode != 0:
            raise SourceError(f"clone of {url} failed: {p.stderr.strip()[:300]}")
    else:
        spec = f"+refs/heads/{branch}:refs/heads/{branch}" if branch else "HEAD"
        git(["fetch", "--depth", "1", "origin", spec], git_dir=gd)
    if want_sha:
        if not git(["cat-file", "-t", want_sha], git_dir=gd, check=False):
            git(["fetch", "--depth", "1", "origin", want_sha], git_dir=gd, check=False)
        if not git(["cat-file", "-t", want_sha], git_dir=gd, check=False):
            raise SourceError(f"locked commit {want_sha[:7]} is not reachable from {url}; run with --refresh to move the lock")
    head = git(["rev-parse", f"refs/heads/{branch}" if branch else "HEAD"], git_dir=gd, check=False)
    if not head:
        head = git(["rev-parse", "HEAD"], git_dir=gd)
    return head


def short(sha: str) -> str:
    return (sha or "")[:7]


def lock_pin(entry: dict) -> str:
    """The short id a citation carries after '@' for this lock entry."""
    if entry.get("commit"):
        return short(entry["commit"])
    return short(entry.get("tree_sha256", ""))
