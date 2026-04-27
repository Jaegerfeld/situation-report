# Releases & Installation

SituationReport is distributed as a standalone desktop app – **no Python, no installation required**.
Just download, unzip, and run.

---

## Download

All available releases are on the [GitHub Releases page](https://github.com/Jaegerfeld/situation-report/releases).

| Release type | Description | When available |
|--------------|-------------|----------------|
| **Stable release** (e.g. `v0.6.0`) | Tested, production-ready build | After each version tag |
| **Dev Build** (`dev-latest`) | Latest development state of `main` | After each merge to `main` |

!!! tip "Which version should I use?"
    For regular use, always pick the **latest stable release**.
    Dev Builds are intended for testing new features and may contain incomplete functionality.

---

## Installation

### Windows

1. Download `SituationReport-Windows.zip`
2. Extract the zip (right-click → *Extract All*)
3. Open the extracted folder and double-click `SituationReport.exe`

!!! note "Windows SmartScreen"
    On the first launch, SmartScreen may show a warning because the app is not signed.
    Click **More info** → **Run anyway**.

---

### macOS (Apple Silicon)

1. Download `SituationReport-macOS-ARM.zip`
2. Extract the zip
3. Optionally move `SituationReport.app` to your *Applications* folder
4. **First launch**: right-click the app → *Open* → confirm *Open* in the dialog

!!! note "macOS Gatekeeper"
    Because the app is not notarized, macOS blocks a direct double-click on the first launch.
    The right-click approach bypasses this protection once.

---

### Linux (x64)

1. Download `SituationReport-Linux.zip`
2. Extract the zip
3. Open a terminal, navigate to the extracted folder, and run:

```bash
chmod +x SituationReport   # once only
./SituationReport
```

---

## Release process (for developers)

### Publishing a stable release

A stable release is triggered by pushing a **version tag** on `main`:

```bash
# Update version in version.py, commit and push, then:
git tag v0.6.0
git push origin v0.6.0
```

GitHub Actions will automatically build all three platforms and publish the release with the ZIP files attached.

Tag naming follows `vMAJOR.MINOR.PATCH` per [SemVer](https://semver.org/).

| Version bump | When |
|--------------|------|
| `PATCH` (`v0.5.0` → `v0.5.1`) | Bug fix |
| `MINOR` (`v0.5.1` → `v0.6.0`) | New feature |
| `MAJOR` (`v0.6.0` → `v1.0.0`) | Breaking change (new file format, etc.) |

### Dev Build

The Dev Build is triggered **automatically** after every merge to `main` – no manual action needed.
The existing `dev-latest` release on GitHub is replaced each time.

---

## GitHub Actions workflows

| Workflow | File | Trigger |
|----------|------|---------|
| Build & Release | `.github/workflows/release.yml` | Push of a `v*` tag |
| Dev Build | `.github/workflows/dev-build.yml` | Merge to `main` |
| Deploy Docs | `.github/workflows/docs.yml` | Changes in `docs/` or `mkdocs.yml` |

### Supported platforms

| Platform | Runner | Output |
|----------|--------|--------|
| Windows | `windows-latest` | `SituationReport-Windows.zip` |
| macOS (Apple Silicon) | `macos-latest` | `SituationReport-macOS-ARM.zip` |
| Linux x64 | `ubuntu-latest` | `SituationReport-Linux.zip` |
