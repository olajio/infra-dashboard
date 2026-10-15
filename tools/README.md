# Tools for MIM V3

The original build scripts lived outside the repo and were lost when the work environment was reset (14 Oct 2026).
Since then `MIM V3.ndjson` is changed by patch scripts kept here, so the work can be repeated and reviewed.

| File | What it does |
|---|---|
| `mim_v3_patch_2026-10-14.py` | The 14 Oct changes (suggestions2.txt): Active P1 / P2 donut, Users impacted demo number, banner removed, Middleware / Database tables, server named on Server Health, Applications on this CI and Changes on 7 days, link-only cards. `python3 mim_v3_patch_2026-10-14.py IN.ndjson OUT.ndjson` (run once, on the version before it) |
| `test_mim_v3_2026-10-14.py` | Loads small known data into a local Elasticsearch (localhost:9200) and checks the changed panels' queries as stored in the dashboard |
| `link_cols.py` + `check_link_columns.js` | Kibana 9.5 blocks links on columns a query creates. `python3 link_cols.py "MIM V3.ndjson" /tmp/linkpanels.json`, copy the JSON and the .js into the Kibana container as `/tmp/linkpanels.json` and `/tmp/check_link_columns.js`, then run `node /tmp/check_link_columns.js` there (Kibana's own `getQuerySummary` decides) |
| `mim_v3_patch_2026-10-15.py` | The 15 Oct fixes to the colleague's export (`updated mim dashboard.ndjson`): related-CI views with exact classes, both directions and the Incident / CI controls; extra control removed; 24 h default; sections expanded and renumbered; Application Health, Services of the Application and the Application control. `python3 mim_v3_patch_2026-10-15.py "updated mim dashboard.ndjson" "MIM V3.ndjson"` |
| `test_mim_v3_2026-10-15.py` | Checks those panels and settings against small known data in a local Elasticsearch |
| `mim_v3_patch_2026-10-16.py` / `test_mim_v3_2026-10-16.py` | The 16 Oct changes (suggestions2.txt update): people columns in Active Incidents and Escalate (Assigned MIM removed), Applications impacted and What this CI runs on removed, Open Alerts 24 h, black Active P1 / P2 donut and Users impacted |

