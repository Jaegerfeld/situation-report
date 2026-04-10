# Modules

SituationReport is structured as a monorepo. Each module is a standalone Python package in the root directory.

```
situation-report/
├── get_data/
├── transform_data/
├── build_reports/
├── testdata_generator/
└── simulate/
```

The modules are independently usable. The typical data flow is:

```
get_data  →  transform_data  →  build_reports
```
