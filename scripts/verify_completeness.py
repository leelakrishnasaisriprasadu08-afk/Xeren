"""
verify_completeness.py — Xeren File Manifest Generator & Verifier
=================================================================
SOURCE machine  : python scripts/verify_completeness.py --generate
FRIEND's machine: python scripts/verify_completeness.py --verify

The manifest (file_manifest.json) is committed to the repo so anyone
who clones can immediately check what files they might be missing.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "file_manifest.json"

# Directories / patterns to skip (mirrors .gitignore logic)
SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    "training", "models",          # large binary dirs
    "data/qdrant_storage", "data/memory",
}
SKIP_EXTS = {
    ".safetensors", ".gguf", ".bin", ".pt", ".pth",
    ".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".sqlite3",
    ".log", ".tmp", ".bak",
}
SKIP_FILES = {".env", ".env.local", ".env.production"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _should_skip(path: Path) -> bool:
    """Return True if this path should be excluded from the manifest."""
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    if path.suffix.lower() in SKIP_EXTS:
        return True
    if path.name in SKIP_FILES or path.name.startswith(".env"):
        return True
    return False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------
def generate_manifest():
    print(f"[+] Scanning {ROOT} …")
    manifest: dict[str, dict] = {}
    skipped = 0

    for f in sorted(ROOT.rglob("*")):
        if not f.is_file():
            continue
        rel = _relative(f)
        if _should_skip(Path(rel)):
            skipped += 1
            continue
        size = f.stat().st_size
        sha = _sha256(f)
        manifest[rel] = {"size": size, "sha256": sha}
        print(f"  ✓  {rel}  ({size:,} bytes)")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as fp:
        json.dump({"version": 1, "root": str(ROOT), "files": manifest}, fp, indent=2)

    print(f"\n[✓] Manifest written → {MANIFEST_PATH}")
    print(f"    Tracked  : {len(manifest)} files")
    print(f"    Skipped  : {skipped} files")
    print(f"\n    Commit file_manifest.json and push — your friend can now run:")
    print(f"    python scripts/verify_completeness.py --verify")


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
def verify_manifest():
    if not MANIFEST_PATH.exists():
        print("[✗] file_manifest.json not found — run --generate first (or pull latest).")
        sys.exit(1)

    with open(MANIFEST_PATH, encoding="utf-8") as fp:
        data = json.load(fp)

    files: dict[str, dict] = data["files"]
    missing, changed, ok = [], [], []

    print(f"[+] Verifying {len(files)} tracked files against {ROOT} …\n")

    for rel, info in files.items():
        local = ROOT / rel
        if not local.exists():
            missing.append(rel)
            print(f"  ✗ MISSING  {rel}")
        else:
            actual_size = local.stat().st_size
            if actual_size != info["size"]:
                changed.append((rel, info["size"], actual_size))
                print(f"  ⚠ SIZE MISMATCH  {rel}  (expected {info['size']:,}, got {actual_size:,})")
            else:
                # Only checksum files smaller than 50 MB to keep it fast
                if actual_size < 50 * 1024 * 1024:
                    actual_sha = _sha256(local)
                    if actual_sha != info["sha256"]:
                        changed.append((rel, info["sha256"], actual_sha))
                        print(f"  ⚠ HASH MISMATCH  {rel}")
                    else:
                        ok.append(rel)
                else:
                    ok.append(rel)   # size matched; skip full hash for large files

    # Summary
    print(f"\n{'='*60}")
    print(f"  OK            : {len(ok)}")
    print(f"  Missing       : {len(missing)}")
    print(f"  Changed/Wrong : {len(changed)}")
    print(f"{'='*60}")

    if missing:
        print("\n[ACTION] Missing files — ask the source for these or re-pull:")
        for f in missing:
            print(f"    {f}")

    if changed:
        print("\n[ACTION] Possibly corrupted or outdated — re-download these:")
        for entry in changed:
            print(f"    {entry[0]}")

    if not missing and not changed:
        print("\n[✓] All files present and accounted for — you are good to go!")
    else:
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Xeren file manifest generator & verifier"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate", action="store_true",
                       help="Generate file_manifest.json (run on source machine)")
    group.add_argument("--verify", action="store_true",
                       help="Verify local files against file_manifest.json")
    args = parser.parse_args()

    if args.generate:
        generate_manifest()
    else:
        verify_manifest()


if __name__ == "__main__":
    main()
