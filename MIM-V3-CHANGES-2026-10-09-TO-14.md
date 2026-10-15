# MIM V3 — changes from Friday 9 Oct to Wednesday 14 Oct 2026, and what is left

## Changes

### Friday 9 Oct
- Fixed links that only worked in edit mode on Kibana 9.5, and wrote up the investigation
  (*MIM-V3-LINKS-INVESTIGATION.md*).
- Renamed the "SRE Dashboard" link to "Applications Operations Dashboard".
- Cut At a Glance to six tiles and made Hotspot CI count P1s per CI, then renamed it "Hotspot CI" (both replaced on
  14 Oct).
- Analysed the CMDB dependency index (Round 6, *MIM-V3-APP-DEPENDENCIES.md*).
- Added the **Applications impacted** tile (section 1).
- Added three CMDB dependency panels (section 2): **Blast radius**, **Applications that depend on this CI** and
  **What this CI runs on**.

### Monday 12 Oct
- Moved the **Incident** control first and the **CI** control second.
- Picking an incident now makes sections 2 and 3 show its affected CI; each incident option shows its CI
  ("INC… · CI").
- Added a Users impacted placeholder tile.
- Split Middleware and Database Health; renamed Infra Health to **Server Health**.

### Tuesday 13 Oct
- Changes limited to the last 7 days (Round 7 queries).
- Added **Alerts on this CI** (section 2): Netcool alerts on the CI, with "likely trigger / earlier / after" timing
  against the picked incident.
- Added **Open Alerts with No Incident** (section 1).
- Added an **Assigned MIM** column to Active Incidents and Escalate: the person who promoted the incident to a major
  incident, or the assignment group's manager when nobody did (Round 8).

### Wednesday 14 Oct (all of `suggestions2.txt`)
- One **Active P1 / P2 donut** replaces the six tiles.
- Users impacted shows a **demo number** (2,500).
- Removed the "Pick the incident…" ribbon.
- **Middleware / Database Health** are now tables: Down / Healthy badge, minutes since seen, and the server, which
  links to the CMDB.
- **Server Health** names the server on each tile.
- **Applications on this CI** and **Changes** look at the last 7 days.
- The section 4 cards show the hyperlinks only.
- Added a `tools/` folder with the patch script, a test and the link checker (the earlier build scripts were lost
  when the work environment was reset).

## Still to do, per the suggestions files

### Not done
1. **"Include a table to automatically select"** (`new_suggestions.txt`). Kibana cannot set a control by clicking a
   table row. An alternative needs agreeing: either a click on Active Incidents applies a filter, or the MIM lead
   keeps using the Incident control.
2. **Number of users likely impacted** from CMDB static user counts or real-user monitoring (RUM). The dashboard shows
   a demo number until ATOS ingests the data.

### Needs clarifying
3. **"Service health"** (`new_suggestions.txt`). Section 3 already has Service health tiles; what is wanted beyond
   that?

### Done, with limits
4. **Alert that resulted in the incident.** Matched by CI and time only, because Netcool alerts carry no incident
   number. An exact link needs the Netcool / ServiceNow integration to write the incident number back to the alert.
5. **Clickable health widgets.** Middleware and Database link to the server in the CMDB. Server Health has no
   click-through, because Kibana 9.5 blocks it on those tiles. Whether the section is "appealing" enough is for the
   client to judge.
6. **Changes, 7 days.** Mostly shows changes on the CI itself. Changes on linked CIs only appear when their CMDB link
   was updated in the same week.
7. **Assigned MIM.** The real MIM shows only on incidents promoted to major incident (last 30 days: 2 of 3 P1s, no
   P2s). Everything else shows the assignment group's manager.

### Other open items, outside the suggestions files
- Live health in *What this CI runs on* needs an `@timestamp` added to the CMDB dependency index.
- Whether to remove *Applications on this CI*: kept for now.
- None of this week's changes have been checked on the Kibana 9.5.3 cluster yet.
