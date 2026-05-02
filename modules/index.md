# Module

SituationReport ist als Monorepo aufgebaut. Jedes Modul ist ein eigenständiges Python-Paket im Stammverzeichnis.

```
situation-report/
├── launcher/
├── get_data/
├── transform_data/
├── build_reports/
├── testdata_generator/
├── helper/
└── simulate/
```

Die Module sind unabhängig voneinander nutzbar. Der `launcher` dient als zentraler Einstiegspunkt. Der typische Datenfluss ist:

```
testdata_generator  →  (helper)  →  transform_data  →  build_reports
get_data            →  (helper)  →  transform_data  →  build_reports
```

`helper` ist optional und wird benötigt, wenn mehrere paginierte JSON-Exporte vor der Transformation zusammengeführt werden müssen.
