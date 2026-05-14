# =============================================================================
# Autor:          Robert Seebauer
# Repository:     https://github.com/Jaegerfeld/situation-report
# KI-Unterstützung: Erstellt mit Unterstützung von Claude (Anthropic)
# Erstellt:       14.05.2026
# Geändert:       14.05.2026
# Lizenz:         BSD-3-Clause (siehe LICENSE)
#
# Fachliche Funktion:
#   Gemeinsames Font-Setup für alle Manual-Generatoren. Registriert eine
#   TrueType-Schriftart mit vollständiger Unicode-Abdeckung (inkl. rumänischer
#   Sonderzeichen ă, ș, ț) und gibt die Fontnamen als Tupel zurück.
#   Suchpfade: docs/assets/fonts/ → Windows-Fonts → Linux-Fonts → ReportLab-Vera
# =============================================================================

from pathlib import Path
import sys
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_PREFIX = "MFSans"

NORMAL      = _PREFIX
BOLD        = _PREFIX + "-Bold"
ITALIC      = _PREFIX + "-Italic"
BOLD_ITALIC = _PREFIX + "-BoldItalic"


def _locate(candidates: list[str]) -> Path | None:
    dirs = [Path(__file__).parent / "assets" / "fonts"]
    if sys.platform == "win32":
        dirs.append(Path(r"C:\Windows\Fonts"))
    elif sys.platform == "darwin":
        dirs += [Path("/Library/Fonts"), Path("/System/Library/Fonts/Supplemental")]
    else:
        dirs += [Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/TTF")]
    try:
        import reportlab
        dirs.append(Path(reportlab.__file__).parent / "fonts")
    except Exception:
        pass
    for d in dirs:
        for name in candidates:
            p = d / name
            if p.exists():
                return p
    return None


def setup() -> tuple[str, str, str, str]:
    """Register a Unicode-capable font family and return (normal, bold, italic, bold_italic)."""
    paths = {
        NORMAL:      _locate(["DejaVuSans.ttf",           "arial.ttf",   "Vera.ttf"  ]),
        BOLD:        _locate(["DejaVuSans-Bold.ttf",       "arialbd.ttf", "VeraBd.ttf"]),
        ITALIC:      _locate(["DejaVuSans-Oblique.ttf",    "ariali.ttf",  "VeraIt.ttf"]),
        BOLD_ITALIC: _locate(["DejaVuSans-BoldOblique.ttf","arialbi.ttf", "VeraBI.ttf"]),
    }
    if all(paths.values()):
        for name, path in paths.items():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        return NORMAL, BOLD, ITALIC, BOLD_ITALIC
    import warnings
    missing = [k for k, v in paths.items() if not v]
    warnings.warn(
        f"Unicode-Font nicht gefunden ({missing}), Fallback auf Helvetica "
        f"(rumänische Sonderzeichen werden nicht korrekt dargestellt)"
    )
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique"
