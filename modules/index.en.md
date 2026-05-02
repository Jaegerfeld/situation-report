# Modules

SituationReport is structured as a monorepo. Each module is a standalone Python package in the root directory.

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

The modules are independently usable. The `launcher` serves as the central entry point. The typical data flow is:

```
testdata_generator  →  (helper)  →  transform_data  →  build_reports
get_data            →  (helper)  →  transform_data  →  build_reports
```

`helper` is optional and is used when multiple paginated JSON exports need to be merged before transformation.
