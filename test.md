Advice only, no changes. First I'm pulling the new file and checking what the exports and notes say about acknowledgement, SLA and change-request data.

The updated export includes my changes, your width edits, and removes "Top 10 Critical Service Error Messages." Now I'll pull together the earlier findings on fields for each question.

Next I'm checking what the earlier sessions recorded about the actual fields on the incident index, and whether a change-request index exists.

The earlier sessions captured a `_cat/indices` listing and the 340-field incident record. Extracting both:

I found two relevant indices, `servicenow-change-requests` and `servicenow-incident-timelines`, which may contain acknowledgement or assignment events. Now checking their sizes and whether any of their fields were ever captured.

An earlier session had already mapped these indices. Pulling that full note, plus the incident field list (looking for change-link, major-incident and SLA fields):

I'll double-check that earlier finding, since the incident mapping actually contains a full `sla.*` tree with breach, end time, and stage fields for each SLA type.

That sample was only 3 open incidents. The guide goes further and says "null even on resolved incidents", so I'm checking whether a resolved-incident query was ever actually run:

The SLA claim traces back to a commit message, not an actual query of resolved incidents' SLA fields. Now I'll scan the full 340-field incident list for a change link (caused_by, rfc) and assignment/acknowledgement timestamps.

That list mixes in fields from other indices, and `acknowledged_at` may only appear because earlier notes mention it. Checking the actual 340-column incident sample on its own:

That parse only caught 102 of the 340 fields. The comma-separated field list the user sent earlier is more complete:

One last check: `cmdb_ci.display_value` appeared in an export earlier, and that's the CI field name ServiceNow uses on change requests.

I've reviewed all three; nothing is built or changed yet. In short: (1) is possible now using stand-in signals, (2) is only partly done and could probably be done properly, and (3) isn't done but should be possible, because your cluster has a change-request index.

I've used `mim_v2_10_1_2026.ndjson` as the starting point. It's my last version with your width changes, and with "Top 10 Critical Service Error Messages" removed.

I can't query your cluster, so this is based on what we've captured before: the index listing, the incident field list and sample records from earlier sessions. Three of the indices that matter have never been sampled, so every "possible" below depends on a quick check (queries at the end).

## 1. Incidents needing MIM attention: possible, but not with a true "acknowledged" field

**Why:** the incident index has no `acknowledged_at` or `assigned_at` field, so it can't say when someone picked an incident up or who did. It does carry enough to flag incidents that look neglected or risky:

| Signal | Field (on the incident) | Confirmed? |
|---|---|---|
| Nobody assigned yet | `assigned_to.name` empty | Yes: populated on 1 of the 3 open incidents in an earlier sample |
| Still "New" after X minutes | `state_name`, `opened_at` | Yes |
| SLA breached / at risk | age rule, or the real SLA (see 2) | Age rule yes |
| Major incident with no bridge | `is_major_incident`, `has_been_handled_by_bridge` | Fields exist; how often they're filled is unknown |
| Bounced between teams | `reassignment_count` (e.g. 3 or more) | Yes |
| Reopened | `reopen_count` > 0 | Yes |
| Many child incidents (wide impact) | `parent_incident.number` | Field exists, unverified |

**What I'd build:** a short "Needs MIM attention" table on the top row. It would list active P1/P2 incidents matching any signal, with a "Reason" column such as "Unassigned 25 min" or "Breached SLA".

**What it can't do:** give a true acknowledgement time (time-to-acknowledge) or say who acknowledged. Two possible sources:
- `servicenow-incident-timelines` (9.9M records), which looks like a log of each incident's state changes. "First move out of New" or "first assignment" there would be a reasonable acknowledgement time.
- The **response** SLA, if ServiceNow fills it. Its "breached" flag means "not responded to in time", which is the acknowledgement concern directly.

If neither works, this is the enrichment request to raise: have ServiceNow send an acknowledged or assigned timestamp.

## 2. Breached / breaching incidents: partly done; a proper panel is likely possible

**What exists now:** only the SLA column in Active Incidents, and it's an approximation. It uses age since opened against the old dashboard's targets (P1 4 h, P2 8 h), with "At risk" from 80 %. There is no separate panel. It also ignores On-Hold pauses, business-hours calendars, response SLAs, and the SLAs your contracts actually define.

**Why the real data isn't used yet:** the SLA data is there but has never been looked at.
- `servicenow-task-sla` has 199k records. This is normally ServiceNow's per-incident SLA table: one row per SLA per incident, with its stage, whether it has breached, the breach time and the percentage elapsed. We've never seen its fields.
- The incident record also has a full `sla.*` group (primary, response, secondary). Each has a breached flag, a planned breach time and a stage.
- Our guide says those incident SLA fields are "null even on resolved incidents". The only evidence I can find is a sample of **3 open incidents**, so that statement may be wrong. It needs one check.

**Conditions a proper panel should treat as breached or breaching** (if the data has them):
- **Response SLA breached:** not picked up in time, which also covers question 1.
- **Resolution SLA breached:** not fixed in time.
- **Breaching soon:** an SLA still running and past 75–80 % of its time, or due within the next N minutes.
- **Paused:** On-Hold stops the SLA clock, so a paused incident shouldn't show as breaching.
- **Several SLAs on one incident:** any breached SLA counts as breached.
- **No SLA attached:** fall back to the age rule, labelled as such.

**Technical note:** Kibana's query language can only look up matching rows from a specially configured "lookup" index, and `task-sla` probably isn't one. The way around it is the one already used on the Operations dashboard: read both indices together and group by incident number.

## 3. Recent changes on a CI: not done; likely possible

**Why it's possible:** your cluster has `servicenow-change-requests`, with 147.5k records. An earlier session wrongly said there was no change data.

**Why it isn't done:**
- We've never seen its fields.
- The incident record doesn't include ServiceNow's "caused by change" link, so we can't say for certain which change caused which incident.

**What I'd build:**
- **Recent Changes:** change number (linked to ServiceNow), CI, type (normal / standard / emergency), state, outcome (successful / successful with issues / unsuccessful), actual start and end, and assignment group. Failed and emergency changes would be highlighted.
- **Active incidents with a recent change on the same CI:** each active P1/P2 next to changes on its Affected CI in, say, the 7 days before it opened.
  - This matches on CI name and time window, so it suggests a likely cause rather than proving one.
  - It misses changes made to a related CI, for example a change to the database behind the affected application.

**What it depends on:**
- The change records' CI field holds the same names as `ci.name` on incidents.
- Actual start and end times and the outcome are filled in.

## What I need from you

Please run these in Discover (ES|QL mode), with the time picker on **Last 1 year** so older records show up. Send me the results, or screenshots of the field lists.

1. **How full the incident SLA, major-incident and assignee fields are.** `COUNT(field)` counts only rows where that field has a value. If assignees are stored as blank text rather than left empty, the `assignee` count will read high; I'll allow for that.
   ```
   FROM servicenow-incidents-*
   | WHERE priority IN (1, 2)
   | EVAL status = CASE(state_name IN ("Resolved", "Closed", "Canceled", "Cancelled"), "closed", "active")
   | STATS incidents = COUNT(*), has_breached_sla = COUNT(has_breached_sla),
           sla_primary = COUNT(sla.primary.task_has_breached), sla_response = COUNT(sla.response.task_has_breached),
           major_flag = COUNT(is_major_incident), bridge_flag = COUNT(has_been_handled_by_bridge),
           assignee = COUNT(assigned_to.name)
     BY status
   ```
2. **The SLA index:**
   ```
   FROM servicenow-task-sla* | LIMIT 5
   ```
3. **The change index:**
   ```
   FROM servicenow-change-requests* | LIMIT 5
   ```
4. **The incident state-change log**, for acknowledgement times:
   ```
   FROM servicenow-incident-timelines* | LIMIT 5
   ```

With those results I can tell you exactly which of these panels can use real data and which need the stand-ins, and then build them.
