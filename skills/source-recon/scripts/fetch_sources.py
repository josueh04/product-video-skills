"""Export every source of a product into products/<slug>/sources/<role>/, read-only, and pin it.

    bin/pvs-py skills/source-recon/scripts/fetch_sources.py <product_dir> [--refresh] [--role ROLE]

For each entry under `sources:` in product.yaml (docs/contracts.md section 2):
- url:  shallow bare clone of the branch into sources/.git-cache/<role>.git, then git archive.
- path to a git repo: git archive of the branch head (the newer of <branch> and origin/<branch>).
  The user's working tree and refs are never touched: no checkout, no fetch, no worktree.
- path that is not a git repo: copied, pinned by a sha256 of its files, "pinned": false.

sources.lock records what was exported. sources/<role>/ is made read-only (chmod -R a-w).
Without --refresh an exported role is left alone; a role that is locked but missing on disk
(a fresh clone of the product repo) is restored at its locked commit, not at the branch head.
"""
import argparse
import sys
from pathlib import Path

import pvs
import srclib as S


def export_role(product: Path, src: dict, lock: dict, refresh: bool) -> list:
    role = src.get("role")
    if not role or "/" in role or role.startswith("."):
        raise S.SourceError(f"bad role {role!r}: use a short id such as frontend or backend")
    dest = product / "sources" / role
    old = lock.get(role)
    notes = []
    if dest.exists() and old and not refresh:
        print(f"{role:10} locked at {S.lock_pin(old)}, already exported (use --refresh to move it)")
        return notes
    restore = bool(old) and not refresh
    branch = src.get("branch", "") or ""
    app_dir = src.get("app_dir", "") or ""
    tmp = product / "sources" / f".{role}.tmp"
    S.remove_tree(tmp)

    if src.get("url"):
        url = src["url"]
        gd = S.cache_git_dir(product, role)
        want = old.get("commit") if restore else None
        head = S.url_clone_or_fetch(url, branch, gd, want_sha=want)
        sha = want or head
        S.export_commit(None, sha, tmp, git_dir=gd)
        entry = {"url": url, "branch": branch, "commit": sha, "fetched_at": S.now(), "app_dir": app_dir}
        kind = "url"
    elif src.get("path"):
        repo = (product / src["path"]).resolve() if not Path(src["path"]).is_absolute() else Path(src["path"])
        if not repo.exists():
            raise S.SourceError(f"{role}: path {src['path']} does not exist (resolved to {repo})")
        top = S.git_toplevel(repo)
        if top is not None and top != repo.resolve() and top not in [product.resolve(), *product.resolve().parents]:
            notes.append(f"{role}: {src['path']} is inside the git repo {top} but is not its root: copied and pinned by a "
                         f"hash of its files. To pin by commit, set path to the repo root and app_dir to the subfolder")
        if S.is_git_root(repo):
            if restore:
                ref, sha = old.get("ref", branch), old["commit"]
                if not S.rev(repo, sha):
                    raise S.SourceError(f"{role}: locked commit {sha[:7]} is gone from {repo}; run with --refresh")
            else:
                ref, sha, warns = S.resolve_local_ref(repo, branch)
                notes += warns
                age = S.fetch_age_days(repo)
                if age is not None and age > 7:
                    notes.append(f"origin refs in {repo.name} were last fetched {age:.0f} days ago; run git fetch there yourself if production may be newer")
                notes += S.other_worktrees(repo, sha)
            S.export_commit(repo, sha, tmp)
            entry = {"path": src["path"], "branch": branch, "ref": ref, "commit": sha,
                     "fetched_at": S.now(), "app_dir": app_dir}
            kind = "git"
        else:
            S.copy_tree(repo, tmp)
            digest = S.tree_sha256(tmp)
            if restore and old.get("tree_sha256") and old["tree_sha256"] != digest:
                notes.append(f"{role}: files changed since the lock (not a git repo, cannot restore the old copy); citations may be stale")
            entry = {"path": src["path"], "tree_sha256": digest, "fetched_at": S.now(),
                     "pinned": False, "app_dir": app_dir}
            kind = "copy"
    else:
        raise S.SourceError(f"{role}: needs url: or path:")

    if app_dir and not (tmp / app_dir).exists():
        notes.append(f"{role}: app_dir {app_dir} is not in the export; fix product.yaml")
    S.remove_tree(dest)
    tmp.rename(dest)
    S.make_read_only(dest)
    lock[role] = entry
    what = "restored" if restore else "exported"
    print(f"{role:10} {kind:4} {(branch or '-')}@{S.lock_pin(entry)}  {what} to sources/{role} (read-only)")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product_dir")
    ap.add_argument("--refresh", action="store_true", help="move each lock to the current branch head")
    ap.add_argument("--role", action="append", help="only this role (repeatable)")
    a = ap.parse_args()

    product = pvs.product_dir(Path(a.product_dir))
    cfg = pvs.load_product(product)
    sources = cfg.get("sources") or []
    if a.role:
        sources = [s for s in sources if s.get("role") in a.role]
        missing = set(a.role) - {s.get("role") for s in sources}
        if missing:
            pvs.die(f"no source with role {', '.join(sorted(missing))} in product.yaml")
    if not sources:
        print("product.yaml has no sources: nothing to fetch (UI can still come from recordings)")
        return 0
    (product / "sources").mkdir(exist_ok=True)
    lock_path = product / "sources.lock"
    lock = pvs.read_json(lock_path, {}) or {}
    failed, notes = 0, []
    for src in sources:
        try:
            notes += export_role(product, src, lock, a.refresh)
        except S.SourceError as e:
            failed += 1
            print(f"{src.get('role', '?'):10} FAILED: {e}", file=sys.stderr)
        pvs.write_json(lock_path, lock)
    known = {s.get("role") for s in (cfg.get("sources") or [])}
    for role in sorted(set(lock) - known):
        notes.append(f"sources.lock has {role}, which product.yaml no longer lists")
    for n in notes:
        print("  note: " + n)
    print(f"sources.lock: {len(lock)} source(s); {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
