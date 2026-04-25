"""
Install project git hooks into .git/hooks/.
Run once after cloning: python scripts/setup_hooks.py
"""
import shutil
import stat
from pathlib import Path

ROOT       = Path(__file__).parent.parent
HOOKS_SRC  = ROOT / "scripts" / "hooks"
HOOKS_DEST = ROOT / ".git" / "hooks"


def install():
    if not HOOKS_SRC.exists():
        print("No hooks directory found at scripts/hooks/ -- nothing to install.")
        return

    installed = 0
    for src in HOOKS_SRC.iterdir():
        if src.suffix in (".py", ".sample"):
            continue
        dest = HOOKS_DEST / src.name
        shutil.copy2(src, dest)
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"  installed: {src.name}")
        installed += 1

    print(f"\n{installed} hook(s) installed into .git/hooks/")


if __name__ == "__main__":
    install()
