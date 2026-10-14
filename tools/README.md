# Tools for MIM V3

The original build scripts lived outside the repo and were lost when the work environment was reset (14 Oct 2026).
Since then `MIM V3.ndjson` is changed by patch scripts kept here, so the work can be repeated and reviewed.

| File | What it does |
|---|---|
| `mim_v3_patch_2026-10-14.py` | The 14 Oct changes (suggestions2.txt): Active P1 / P2 donut, Users impacted demo number, banner removed, Middleware / Database tables, server named on Server Health, Applications on this CI and Changes on 7 days, link-only cards. `python3 mim_v3_patch_2026-10-14.py IN.ndjson OUT.ndjson` (run once, on the version before it) |
| `test_mim_v3_2026-10-14.py` | Loads small known data into a local Elasticsearch (localhost:9200) and checks the changed panels' queries as stored in the dashboard |
| `link_cols.py` + `check_link_columns.js` | Kibana 9.5 blocks links on columns a query creates. `python3 link_cols.py "MIM V3.ndjson" /tmp/linkpanels.json`, copy the JSON and the .js into the Kibana container as `/tmp/linkpanels.json` and `/tmp/check_link_columns.js`, then run `node /tmp/check_link_columns.js` there (Kibana's own `getQuerySummary` decides) |
