"""
Reads __version__ from version.py and updates the version badge in README.md.
Called by the git pre-commit hook when version.py is staged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
VERSION_FILE = ROOT / "version.py"
README_FILE  = ROOT / "README.md"


def read_version() -> str:
    text = VERSION_FILE.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not m:
        print("update_readme_version: could not find __version__ in version.py", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def update_readme(version: str) -> bool:
    text = README_FILE.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r'^\*\*Version [0-9]+\.[0-9]+\.[0-9]+\*\*',
        f'**Version {version}**',
        text,
        flags=re.MULTILINE,
    )
    if n == 0:
        print("update_readme_version: version badge not found in README.md", file=sys.stderr)
        return False
    if new_text == text:
        return False  # nothing changed
    README_FILE.write_text(new_text, encoding="utf-8")
    return True


if __name__ == "__main__":
    version = read_version()
    changed = update_readme(version)
    if changed:
        print(f"update_readme_version: README.md updated to Version {version}")
