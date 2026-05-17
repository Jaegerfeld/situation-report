# Entwicklung

## Voraussetzungen

- Python >= 3.11
- Git

## Setup

```bash
git clone https://github.com/Jaegerfeld/situation-report.git
cd situation-report
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -e ".[docs]"
```

## Dokumentation lokal vorschauen

```bash
mkdocs serve
```

Die Dokumentation ist dann unter [http://127.0.0.1:8000](http://127.0.0.1:8000) erreichbar.

## Branch-Konvention

Neue Arbeiten an einem Modul erfolgen auf einem eigenen Branch:

```
dev/<modulname>
```

Nach Abschluss wird ein Pull Request auf `main` erstellt. Der fertige Stand wird mit einem Tag versehen, der dem Modulnamen entspricht (z. B. `transform_data`).

## Technologie-Stack

| Bereich | Technologie |
|---------|------------|
| Sprache | Python >= 3.11 |
| Paketmanagement | pip / pyproject.toml |
| Versionskontrolle | Git / GitHub |
| Dokumentation | MkDocs + Material Theme |
| Datenquelle | Jira REST API |
| Ausgabeformat | XLSX (openpyxl) |
