# MIM V3: links work in edit mode but not in view mode (investigation)

**Status:** open, waiting on three checks from Kibana 9.5.3 (see *Next steps*) · **Last updated:** 9 Oct 2026
**Dashboard:** MIM V3 (`MIM V3.ndjson`) · **Kibana:** 9.5.3 (build 2026-09-01)

## The problem

The ServiceNow and APM links on MIM V3 tables and charts work when the dashboard is in **edit mode**, but not in
**view mode**. This affects every linked column: Incident, Affected CI, Change, the CI in Escalate, business
applications, and the service links in section 3.

Example (`broken_link.png`): in *Business applications impacted*, selecting "Document Management Facility" does not
open the CMDB link in view mode.

Timeline:

| Date | What happened |
|---|---|
| 8 Oct | First reported: links only work in edit mode |
| 8 Oct | After re-importing the next version, links worked in view mode ("maybe a glitch") |
| 9 Oct | Broken again in view mode across every linked column; still fine in edit mode |

## How the links work

Kibana has no clickable links inside table cells for these (ES|QL) panels. Each link is a **URL drilldown** on the panel:

1. hover over a value and click the small **⊕** (*Filter for*) at the top-left of the cell, or click a bar or tile;
2. Kibana opens a menu: *Apply filter to current view* plus the panel's links (e.g. *Open CI in ServiceNow CMDB*);
3. choosing a link opens it in a new tab.

Clicking the cell text itself does nothing, in either mode.

URL drilldowns need a Gold or higher licence. That is not the problem here, because the links work in edit mode on the
same cluster.

## What has been checked

| Check | Result |
|---|---|
| Local test, Kibana 9.4.1 (trial licence), same `MIM V3.ndjson` | The link menu appears and the ServiceNow / APM tab opens in **both** view and edit mode, including after switching edit → view |
| How MIM V3 stores its links | The `drilldowns` format, the same one Kibana 9.5.3 itself wrote in the exports from this cluster (`current_mim_v1.ndjson`, `mim_v2_10_1_2026.ndjson`, `current_operations_infra_dashboard.ndjson`). The file is not in an old or unsupported format. |
| How MIM V3 describes each panel's data | Same structure as panels exported from this 9.5.3 cluster |
| Which columns are clickable | Only columns named after a real field (`ci.name`, `number`, `service.name` …); see *KIBANA-LIMITATIONS.md*, row 23. Correct for the linked columns. |
| Screenshot (`broken_link.png`) | The selected cell shows the ⊕ / ⊖ / expand buttons, with ⊕ and ⊖ fainter than expand. It is not clear whether they are disabled or just styled for the dark theme. |
| Kibana 9.5.3 locally | Not possible: no 9.5 image is available in the test environment, so the exact cluster behaviour cannot be reproduced |

## Leads

**Kibana 9.5 rewrote drilldowns.** Kibana PR #252976 replaced the drilldown architecture. It has already caused at
least one URL drilldown regression: the link's displayed name was no longer filled in. That bug was fixed in
[PR #290363](https://github.com/elastic/kibana/pull/290363) (merged 11 Sep 2026, backported to 9.4.8 and 9.5.5;
[9.5 backport PR #290628](https://github.com/elastic/kibana/pull/290628)). That fix is about the name, not view mode,
and no public report of a view-mode-only failure was found. But the rewrite is the most likely area for a 9.5-specific
problem, and 9.5.3 predates the fix.

**Unsaved browser state.** Kibana keeps unsaved dashboard changes in the browser and re-applies them after a re-import
(the same mechanism that once dropped the Incident control). This could explain "worked after a re-import, broke
later", but not "works in edit mode, fails in view mode" in the same session. Not yet ruled out.

## Next steps (in progress)

Three checks on the 9.5.3 cluster, in **view mode**:

1. **The click itself.** Hover over a linked value (e.g. "Document Management Facility"), click **⊕**, and note what
   happens:
   - a menu with *Apply filter* and *Open … in ServiceNow* appears;
   - a filter is added with no menu;
   - nothing happens.
2. **Older dashboards.** Open MIM V1 or MIM V2 (built and exported on this 9.5.3 cluster) and click one of their
   ServiceNow links the same way.
   - If they fail too, this is Kibana 9.5 behaviour, not MIM V3.
   - If they work, the problem is specific to MIM V3 and the file will be investigated further.
3. **Browser console.** Press F12 → *Console*, click the link in view mode, and capture any red errors.

| If … | Then |
|---|---|
| Older dashboards fail the same way | Kibana 9.5.3 issue: ask the Kibana administrators about upgrading to 9.5.5 or later, and raise an Elastic support case or GitHub issue with the steps above |
| Only MIM V3 fails | Compare MIM V3's panels with a working MIM V2 panel on 9.5.3 and change the file to match |
| Console shows an error | The error message points to the cause |

## Workaround until then

Links work in edit mode. During a bridge:

1. click **Edit**;
2. use the links;
3. click **Exit edit → Discard changes**. Do not save.

After importing a new version of `MIM V3.ndjson`, always do **More (⋯) → Reset changes**, then reload the page.

## References

- [elastic/kibana PR #290363: fix Go to URL drilldown name templates (regression from PR #252976)](https://github.com/elastic/kibana/pull/290363)
- [elastic/kibana PR #290628: backport of that fix to 9.5](https://github.com/elastic/kibana/pull/290628)
- [Elastic docs: drilldowns (use the cell **+** in view mode to open the drilldown menu)](https://docs-v3-preview.elastic.dev/elastic/docs-content/pull/7129/explore-analyze/dashboards/drilldowns.md)
- [Elastic Discuss: Drilldown option not showing](https://discuss.elastic.co/t/drilldown-option-not-showing/314442.md)
- In this repo: *KIBANA-LIMITATIONS.md* (rows 23–24), *MIM-V3-GUIDE.md* (Clicks and links; Importing), `broken_link.png`
