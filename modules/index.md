# Module

SituationReport ist als Monorepo aufgebaut. Jedes Modul ist ein eigenständiges Python-Paket im Stammverzeichnis.

```
situation-report/
├── launcher/
├── get_data/
├── transform_data/
├── build_reports/
├── testdata_generator/
└── simulate/
```

Die Module sind unabhängig voneinander nutzbar. Der `launcher` dient als zentraler Einstiegspunkt. Der typische Datenfluss ist:

```
get_data  →  transform_data  →  build_reports
```
