# Module

SituationReport ist als Monorepo aufgebaut. Jedes Modul ist ein eigenständiges Python-Paket im Stammverzeichnis.

```
situation-report/
├── get_data/
├── transform_data/
├── build_reports/
├── testdata_generator/
└── simulate/
```

Die Module sind unabhängig voneinander nutzbar. Der typische Datenfluss ist:

```
get_data  →  transform_data  →  build_reports
```
