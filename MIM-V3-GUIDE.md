# MIM V3 — how a Major Incident Manager uses the dashboard

**File:** `MIM V3.ndjson` · **Dashboard:** MIM V3 · **Built from:** Naveen's MIM sketch (`naveen-mim suggestion.png`)
**Default time range:** last 24 hours, refreshing every 5 minutes

MIM V3 answers three questions, in order:

1. **What is going on?** Every active P1 / P2 incident across the estate, how old it is, where it sits and what
   state it is in.
2. **Why, and how bad?** Everything Elastic knows about the one CI behind the incident: its own health, the
   middleware and processes on it, the applications that depend on it, whether customers are feeling it, what the
   logs say and what changed on it recently.
3. **Who do we call?** The CI's support group and the group each incident is with, with one-click links into
   ServiceNow.

The dashboard has two sections and two controls:

| | What it covers | Time window |
|---|---|---|
| **CI control** (top) | Picks the CI that section 2 investigates. Lists the CIs with P1 / P2 incidents in the last month; type to search. *(no CI selected)* clears it. | — |
| **Incident control** (top) | Narrows the *Escalate* panel and the *P1 Duration* tile to one active P1 / P2 incident. *(all incidents)* clears it. No other panel uses it. | — |
| **1 · Major Incident Overview** | All active P1 / P2 incidents, all CIs | Fixed last month (*Active P1 / P2 by Age*: last 7 days) |
| **2 · Investigate the CI** | The CI picked in the control only | Time picker (last 24 h by default), except where a panel says otherwise |

---

## The walkthrough — telling the story

*Example used below: it is 09:00, the bridge line is quiet, and a P1 has just come in.*

### Step 1 — Spot the incident (section 1, top row)

The MIM lead opens MIM V3 and reads the top row from left to right.

- **P1 Duration.** How long the longest-running active P1 has been open, its number and how many P1s are open.
  When the lead picks an incident in the Incident control, the tile shows that incident instead.
- **Incidents (P1 / P2) over time.** Is today normal? A P1 or P2 line that jumps above the rest of the month is the
  first sign of a major incident: many tickets for what is usually one failure.
- **Active P1 / P2 by Age.** Active incidents opened in the last 7 days, grouped as < 1h, 1 - 4h, 4 - 8h, 8 - 24h
  and 1 - 7d. Anything
  orange or red (older than a day) has been sitting too long and is a candidate for escalation, whatever else is
  happening today.
- **Active P1 / P2 by CI.** If one CI has several incidents against it, that CI is very likely the centre of the
  problem. *In the example, three incidents point at `kau1s054`.*
- **Active P1 / P2 by State.** A big "New" slice means incidents nobody has picked up yet.

### Step 2 — Pick the incident (section 1, table)

**Active Incidents (P1 / P2)** lists every active P1 / P2, P1 first and oldest first. For each one the lead sees:

- the **SLA**: Breached, Breaching, Paused or Within SLA, taken from ServiceNow's SLA records. How this is worked
  out is explained in *MIM-V3-SLA-CALCULATION.md*;
- the assignment group, the age and the description.

*In the example, the P1 on `kau1s054` shows SLA Breached.* The lead clicks the incident to open it in ServiceNow if
needed, then **selects `kau1s054` in the CI control**.

### Step 3 — Measure the impact (section 2)

Section 2 now shows `kau1s054` only.

- **Applications on this CI** — the blast radius. The applications and software that run on or depend on the CI
  (from the CMDB relationships) and the APM services sending data from it. *Three applications live on this
  server, including the policy-admin service.*
- **SLO Error Burn Rate** — are customers feeling it? The CI's own SLOs (marked ★) first, then every SLO burning its
  error budget right now. *policy-admin is burning at 38× — well past the 14.4× "page now" level.*
- **Synthetics Health** — does the CI answer from outside? *The ping monitor for the server is down.*

At this point the lead knows the incident is real, customer-facing and tied to one server.

### Step 4 — Confirm it is this CI (section 2)

- **Infra Health** — the server's own telemetry: minutes since it last reported, CPU, memory, fullest disk, each
  green / amber / red. *CPU is at 92 % and the disk is 88 % full.*
- **Middleware / DB Health** — the SQL Server, IBM MQ, IBM HTTP Server, JBoss, WebSphere and Windows middleware
  services on the CI: healthy vs down. *Two components are down.*

### Step 5 — Find the cause (section 2)

- **Process Health** — which process or service actually stopped. *The SQL Server Windows service is Stopped and an
  IBM HTTP Server instance has not been seen for 25 minutes.*
- **Errors from the Logs** — the warning-and-worse lines from the CI's server and application logs, grouped by
  message. *"MSSQLSERVER terminated unexpectedly", followed by SQL timeouts in policy-admin.*
- **Changes on this CI and linked CIs** — was there a change just before? On the CI itself and on CIs linked to it
  in the CMDB (its ESX host, cluster, switch, applications). *An emergency change on `kau1s054` ended unsuccessful
  two hours before the incident opened.*

The story is now complete: an unsuccessful emergency change stopped SQL Server on `kau1s054`, which took down
policy-admin and the applications that depend on it.

### Step 6 — Escalate

**Escalate** gives the lead the people to call without leaving the dashboard. It has one row per active P1 / P2
incident on the CI, showing the incident, its priority and its assignment group, next to the CI's class,
environment and CMDB support group. With several incidents on the CI, pick one in the **Incident control** to show
only that one. Only the CI and the Active Incident are links; clicking either opens it in ServiceNow.

The lead now:

- declares a major incident if several applications are affected or an SLO is past the page-now level;
- opens the bridge and engages the CI support group, the incident's assignment group and the team that made the
  change (the Changes panel shows its group);
- shares the evidence: the burn-rate chart, the stopped service, the first error and the change.

During the bridge the dashboard keeps refreshing every five minutes, so the lead can watch the SLO burn fall back
below 1×, the service return to Running and the ping monitor go green.

---

## Panel reference

**Status:** ✅ ready on the confirmed data · ⚠️ ready, with the limit noted.

| Section | Panel | Status | What it shows | How it works |
|---|---|---|---|---|
| Control | **CI** | ✅ | The CI to investigate | Lists every CI with a P1 / P2 opened in the last 31 days, plus *(no CI selected)*. A query variable (`?ci`) that every section-2 panel uses. |
| Control | **Incident** | ✅ | One incident for *Escalate* and *P1 Duration* | Lists every active P1 / P2 incident, plus *(all incidents)*. A query variable (`?incident`) used only by those two panels. |
| 1 | **P1 Duration** | ✅ | How long an incident has been open (e.g. "1h 14m", "3d 4h") | With *(all incidents)*: the longest-running active P1, titled "Longest: INC… · n active P1s". With an incident picked: that incident ("INC… · P2"), whatever its priority. Counted from `opened_at`; there is no "declared major incident" time in the data. |
| 1 | **Incidents (P1 / P2) over time** | ✅ | New P1 / P2 per day, one line each: P1 (red), P2 (amber) | `servicenow-incidents-*`, counted by opened day over the last 30 days; days with none show 0 |
| 1 | **Active P1 / P2 by Age** | ✅ | Active incidents aged < 1h, 1 - 4h, 4 - 8h, 8 - 24h, 1 - 7d | Active P1 / P2 opened in the last 7 days (fixed). Active = priority 1 / 2 and state not Resolved, Closed, Canceled, Cancelled; age from opened time. Older active incidents are not counted here; they still appear in *Active Incidents*. |
| 1 | **Active P1 / P2 by CI** | ✅ | The 10 CIs with the most active P1 / P2 | Grouped by the incident's Affected CI |
| 1 | **Active P1 / P2 by State** | ✅ | New / In Progress / On-Hold | Grouped by state |
| 1 | **Active Incidents (P1 / P2)** | ✅ | Every active P1 / P2 with SLA, group, age | Incidents joined to `servicenow-task-sla` (real SLA: breached, breaching ≥ 75 % or due in 30 min, paused). No SLA record → age rule (P1 4 h, P2 8 h), marked "(age)". Full rules: *MIM-V3-SLA-CALCULATION.md*. Incident and CI link to ServiceNow. |
| 2 | **How to use this section** | ✅ | One-line instruction | Text panel |
| 2 | **Escalate** | ✅ | One row per active P1 / P2 on the CI: CI, Active Incident, Priority, Class, Env, CI support group, Assignment Group | Incidents on the CI (or the one in the Incident control) plus the CMDB enrichment on its server metrics; last month. CI and Active Incident link to ServiceNow; no other column is clickable. A CI with no active P1 / P2 still shows one row with its owners. If an incident is picked whose CI is not the one in the CI control, Class / Env / support group come from the incident record and may show "—". |
| 2 | **Infra Health** | ✅ | Minutes since last data, CPU p90, peak memory, fullest disk — RAG coloured | System metrics matched on `ci.name` (equal to the host name). Amber ≥ 80 %, red ≥ 90 %; red if silent > 10 min. Empty if the CI is not a monitored server. |
| 2 | **Middleware / DB Health** | ✅ | Healthy vs Down components on the CI | SQL Server metrics (`metricbeat-*` sql / mssql), middleware processes labelled by the Paladin monitoring enrichment (IBM MQ, IHS, JBoss, WebSphere) and Windows middleware services. Down = stopped or silent > 10 min. |
| 2 | **Applications on this CI** | ⚠️ | Applications and software linked to the CI, and APM services on it | `cmdb-ci-relations` ("Runs on", etc., application-type CIs only) + APM services that sent data from the server in the last day. **Limit:** APM services running in Kubernetes report pod names, not the server, so they don't appear; fixed 30-day window. |
| 2 | **SLO Error Burn Rate** | ⚠️ | 1-hour burn rate per SLO: page now (≥ 14.4×), burning (≥ 1×), on track | `.slo-observability.summary-*` (173 Kibana SLOs). The CI's own per-CI SLOs (★) first, then every SLO burning ≥ 1×. **Limit:** Kibana cannot combine SLO summaries with timestamped data in one panel, so for service SLOs it cannot filter to "services on this CI" — compare names with *Applications on this CI*. Viewers need read access to the hidden `.slo-observability.*` indices. |
| 2 | **Synthetics Health** | ✅ | Monitors that target the CI: status now, down checks | `synthetics-*`, ping monitors enriched with the CI, or monitors whose URL is the CI's host name. Browser journeys are tagged with the application, so they do not appear here. |
| 2 | **Errors from the Logs** | ✅ | Warning-and-worse log lines from the CI, grouped by message | Syslog (server, WebSphere, JBoss, Red Hat, AIX, system), generic file logs, APM error and application logs, matched on `ci.name`; syslog severity code ≤ 4 or log level warning or worse; numbers replaced by # so repeats group together |
| 2 | **Process Health** | ✅ | Stopped / not-seen processes and services first, then healthy middleware | Windows services (Stopped = Automatic service not running) and Paladin-labelled middleware processes; Not seen = silent > 10 min |
| 2 | **Changes on this CI and linked CIs** | ⚠️ | Changes active in the last 7 days on the CI and on CMDB-linked CIs; the CI column shows which | `servicenow-change-requests` + `cmdb-ci-relations`. The selected CI's own changes first. Type (Emergency in red), category, state, outcome (close code), planned start, end, group. **Limit:** no actual start and no maintenance windows in the data; "application" category is the nearest thing to a release. Change and CI link to ServiceNow. |

---

## Known limits and the enrichment they point to

| Limit | Why | What would fix it |
|---|---|---|
| No acknowledgement time (time to acknowledge) | Incidents carry no assigned / acknowledged timestamps; the response SLA says *whether* it was met, not *when* | ServiceNow: send assigned / acknowledged timestamps |
| No maintenance windows or releases | No outage-window or actual-start values on 148k change requests; no release or maintenance index | ServiceNow: export maintenance schedules and releases (or Caused-by-change on incidents) to Elastic |
| Change → incident link is inferred | Incidents have no "Caused by change"; matched on the same CI within 7 days | ServiceNow: send Caused-by-change |
| SLO panel not filtered to the CI's services | Kibana limitation (see *KIBANA-LIMITATIONS.md*) | Group SLOs by `ci.name` in Kibana where it makes sense — those follow the CI control |
| Major-incident and bridge flags unused | `is_major_incident` and `has_been_handled_by_bridge` are empty on all P1 / P2 for a year | ServiceNow integration mapping |
| Containerised services not linked to servers | APM reports pod names | Expected; use the application / SLO panels |
| Estimated user base | Not in Elastic | Add the ServiceNow user-base field to the CI enrichment |

## Importing

Import `MIM V3.ndjson` in **Stack Management → Saved objects → Import**. It contains only the dashboard: every
panel is ES|QL, so no data views are needed. MIM V1 and MIM V2 are untouched.

**Re-importing a new version over an older one.** If you had the old version open and changed anything (picked a
CI, changed the time range, entered edit mode), Kibana keeps those unsaved changes in the browser and lays them over
the imported version, including the old set of controls. New controls then go missing and the panels that use
them fail with *Unknown query parameter [incident]*. To fix it:

1. Open MIM V3 and click **More (⋯) → Reset changes → Reset dashboard**. In edit mode, click **Exit edit** and
   discard first.
2. **Reload the page.** Both the CI and Incident controls are back.

Do **not** click Save while the dashboard is in that state: it would save the dashboard without the new controls.
If that has happened, import `MIM V3.ndjson` again (overwrite), then do steps 1 and 2.
