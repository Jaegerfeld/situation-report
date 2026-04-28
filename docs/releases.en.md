# Releases & Installation

SituationReport is distributed as a portable package – all source files, scripts, and configuration options are included.
Download, unzip, and run.

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
3. In the extracted folder:
   - Double-click `BuildReports.bat` → Build Reports GUI
   - Double-click `TransformData.bat` → Transform Data GUI

!!! note "Windows SmartScreen"
    On the first launch, SmartScreen may show a warning because the included files are not signed.
    Click **More info** → **Run anyway**.

!!! info "Includes Python and Chrome"
    The Windows package includes Python 3.11 and Chrome (for PDF export) – no internet or separate installation required.

---

### macOS (Apple Silicon)

1. Download `SituationReport-macOS-ARM.zip`
2. Extract the zip
3. Right-click `BuildReports.command` → *Open* → confirm *Open* in the dialog

!!! note "macOS Gatekeeper"
    Because the scripts are not notarized, macOS blocks a direct double-click on the first launch.
    The right-click approach bypasses this protection once.

!!! warning "One-time setup (first launch)"
    On the first launch, a Python environment is set up automatically (~1 minute).
    **Internet required.** After that, the app works offline.

---

### Linux (x64)

1. Download `SituationReport-Linux.zip`
2. Extract the zip
3. Check prerequisites:
   ```bash
   python3 --version           # 3.11 or newer
   python3 -c "import tkinter" # must run without error
   ```
   If tkinter is missing: `sudo apt install python3-tk` (Ubuntu/Debian) or `sudo dnf install python3-tkinter` (Fedora)
4. Run from the extracted folder:
   ```bash
   ./BuildReports.sh    # Build Reports GUI
   ./TransformData.sh      # Transform Data GUI
   ```

!!! warning "One-time setup (first launch)"
    On the first launch, a Python environment is set up automatically (~1 minute).
    **Internet required.** After that, the app works offline.

---

## Package contents

The package contains the full repository – source files, configurations, and examples:

| File / Folder | Contents |
|---------------|----------|
| `build_reports/` | Metrics, GUI, CLI, and plugin mechanism |
| `transform_data/` | Data transformation (Jira export → XLSX) |
| `get_data/` | Data access |
| `simulate/` | Simulation and test-data generation |
| `testdata_generator/` | Example workflows and test data |
| `build_reports/pi_config_example.json` | Template for PI configuration |
| `BuildReports.bat/.command/.sh` | Launcher for Build Reports |
| `TransformData.bat/.command/.sh` | Launcher for Transform Data |

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

| Platform | Runner | Output | Python |
|----------|--------|--------|--------|
| Windows | `windows-latest` | `SituationReport-Windows.zip` | Embeddable 3.11 (bundled) |
| macOS (Apple Silicon) | `macos-latest` | `SituationReport-macOS-ARM.zip` | System Python + venv (on 1st launch) |
| Linux x64 | `ubuntu-latest` | `SituationReport-Linux.zip` | System Python + venv (on 1st launch) |
