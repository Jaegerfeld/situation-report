# transform_data

Transforms raw Jira data (issue export) into stage-time metrics (IssueTimes.xlsx, CFD.xlsx, Transitions.xlsx).

**Status:** available

## Manuals

| Language | Download |
|----------|----------|
| Deutsch (DE) | [Benutzerhandbuch](../transform_data_Benutzerhandbuch.pdf) |
| English (EN) | [User Manual](../transform_data_UserManual.pdf) |
| Română (RO) | [Manual de Utilizator](../transform_data_ManualUtilizator.pdf) |
| Português (PT) | [Manual do Utilizador](../transform_data_ManualUtilizador.pdf) |
| Français (FR) | [Manuel d'utilisation](../transform_data_ManuelUtilisateur.pdf) |

## Data hand-over to build_reports

After a successful transformation, the **Open in build_reports** button hands
the three generated XLSX files and the workflow file straight to `build_reports`.
The reports GUI opens with those file fields already filled in — there is no
need to re-select the files manually.

If you have a project template loaded (Templates → Load), its build_reports
settings — PI config, filters, metric selection — are carried over into the
hand-over as well, so `build_reports` opens fully configured. Without a loaded
template the PI config and filters are left for you to choose.
