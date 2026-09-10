# tests/testdata

Getrackte Snapshots, auf die die Testsuite und die Handbuch-Generatoren zeigen.
Sie sind **Abbild der Pipeline**, nicht handgepflegt: Ändert sich das Format,
das `transform_data` schreibt, müssen sie im selben Commit neu erzeugt werden.

## ART_A

Quelle ist `ART_A/ART_A.json` (Jira-Export, 533 Vorgänge, erstellt zwischen
02.12.2023 und 30.11.2025). Abbildung über `ART_A/workflow_ART_A.txt`
(`workflow_ART_A_incomplete.txt` und `workflow_ART_A_status_missing.txt` sind
Fehlerfälle für eigene Tests, keine Erzeugungsgrundlage).

Neu erzeugen:

```
./.venv/Scripts/python.exe tests/testdata/_regenerate_cfd.py
```

Das Skript schreibt **nur** `ART_A_CFD.xlsx`. `REFERENCE_DT` ist darin auf den
15.04.2026 festgenagelt — das ist der einzige Wert, der den letzten Tag der
Datei bestimmt, und er bleibt fest, damit sich beim Neuerzeugen der Zeitraum
nicht verschiebt.

`ART_A_IssueTimes.xlsx` und `ART_A_Transitions.xlsx` werden **nicht** vom Skript
erzeugt. Sie stammen aus einem Lauf vom 16.04.2026 und sind aktuell.

### Was in `ART_A_CFD.xlsx` steht

Je Tag und Stage die Zahl der Vorgänge, die an diesem Tag **in diese Stage
eingetreten** sind — keine Bestandszahlen. `build_reports` kumuliert selbst.
Die meisten Tage sind deshalb Nulltage, und die Spaltensummen liegen in der
Größenordnung der Vorgangszahl, nicht im fünfstelligen Bereich.

Grobe Probe nach dem Neuerzeugen: 866 Zeilen, 02.12.2023 bis 15.04.2026,
`Done` ≈ 338 bei 533 Vorgängen, 289 Tage mit Werten ungleich null.

## ART_E

Hat kein `ART_E.json` im Repository und lässt sich hier nicht neu erzeugen.
Die Dateien tragen bereits Eintrittszählungen und sind in Ordnung.
