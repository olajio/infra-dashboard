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
| `mim_v3_patch_2026-10-16.py` / `test_mim_v3_2026-10-16.py` | The 16 Oct changes (suggestions2.txt update): people columns in Active Incidents and Escalate (Assigned MIM removed), Applications impacted and What this CI runs on removed, Open Alerts 24 h, Active P1 / P2 as a Vega donut, Users impacted text (both black until the second round below) |

| `mim_v3_patch_2026-10-16b.py` / `test_mim_v3_2026-10-16b.py` | The second 16 Oct round: CMDB status removed from the four section 3 views, Active P1 / P2 and Users impacted transparent with theme text colours, descriptions that named removed panels corrected. Run the 15 Oct test before this test (it loads the dependency data) |
| `mim_v3_patch_2026-10-16d.py` / `test_mim_v3_2026-10-16d.py` | P3 incidents included: Incident and CI controls, Active donut (P3 blue), Active Incidents (a P3 with no SLA record shows "No SLA record"), Escalate. Time to Resolve stays P1 / P2. Run after `mim_v3_patch_2026-10-16b.py`; the test cleans up its own data |

To rebuild `MIM V3.ndjson` from the colleague's export, run the patches in order:
`mim_v3_patch_2026-10-15.py "updated mim dashboard.ndjson" "MIM V3.ndjson"`, then `mim_v3_patch_2026-10-16.py "MIM V3.ndjson" "MIM V3.ndjson"`, then `mim_v3_patch_2026-10-16b.py "MIM V3.ndjson" "MIM V3.ndjson"`, then `mim_v3_patch_2026-10-16d.py "MIM V3.ndjson" "MIM V3.ndjson"`.
Tests: `test_mim_v3_2026-10-14.py`, `-16.py`, `-15.py`, `-16b.py`, `-16d.py`, each with `"MIM V3.ndjson"`, against a local Elasticsearch on port 9200.
