# MIM V3: how the SLA column is calculated

**Panel:** *Active Incidents (P1 · P2 over 8 h · P3 over 24 h)*, section 1 of MIM V3 · **Column:** SLA

The SLA column shows the **worst SLA on each incident**, read from ServiceNow's own SLA records. Whether an incident
is **Breached** is ServiceNow's verdict: the `task_has_breached` flag on its SLA records. The dashboard never decides
a breach from the incident's age (agreed with the ServiceNow team, 27 Oct 2026; see `sla_breached.txt`).

---

## 1. Where the data comes from

| Index | What it gives | Key fields |
|---|---|---|
| `servicenow-incidents-*` | The incident: priority, state, opened time | `number`, `priority`, `state_name`, `opened_at` |
| `servicenow-task-sla-*` | One record per SLA attached to an incident (response, resolution …) | `task_number` (= incident number), `task_has_breached`, `stage`, `percentage`, `planned_end_time` |

`servicenow-task-sla` is an alias over rollover indices (`servicenow-task-sla-000001`, …). The dashboard reads
`servicenow-task-sla-*`, which matches every generation, including ones created after the next rollover. Each SLA
record is one document (its id is the record's `sys_id`), updated in place. Every record has `task_has_breached`
(200,617 of 200,617 on 26 Oct 2026).

The two are matched on **incident number** (`number` = `task_number`). An incident can have several SLA records,
one per contract (for example a P2-P4 resolution SLA and a vendor-specific one).

Only **active** incidents are listed: priority 1, 2 or 3 and the incident's **latest record** (highest
`@timestamp`) not On Hold, Resolved, Closed, Canceled or Cancelled. The table then keeps every P1, and only the P2s
open longer than 8 h and the P3s open longer than 24 h.

## 2. Step 1: rate each SLA record

Each SLA record gets one status. The rules are checked in this order, and the first match wins.

| Rank | Status | Rule (on the SLA record) |
|---|---|---|
| 1 | **Breached** | `task_has_breached` is true |
| 2 | **Breaching** | `stage` is `in_progress` **and** either `percentage` ≥ **75 %** or `planned_end_time` is within the next **30 minutes** (or already passed) |
| 3 | **Paused** | `stage` is `paused` (the SLA clock is stopped) |
| 4 | **Within SLA** | `stage` is `in_progress`, with no rule above matching |
| 5 | **Met** | Any other stage, such as `completed`, without a breach |
| — | *(ignored)* | `stage` is `cancelled`, even if it was flagged as breached (a cancelled SLA no longer applies, e.g. after a priority change) |

An SLA whose planned end has passed but whose flag is still false shows **Breaching**, not Breached: ServiceNow sets
the flag on its own schedule, and the dashboard waits for it.

## 3. Step 2: one SLA per incident (the worst one)

The incident shows the **lowest rank** among its SLA records, which is the worst status. For example, if one SLA is
Breached and another is Within SLA, the incident shows **Breached**.

## 4. No SLA record

If an incident has no (non-cancelled) SLA record synced in the last 7 days, the column shows **No SLA record**. The
incident's age is not used to guess a status.

## 5. Colours

| Status | Colour |
|---|---|
| Breached | Red |
| Breaching | Amber |
| Paused, No SLA record | Grey |
| Within SLA, Met | Green |

## 6. Worked examples

| Incident | SLA records | Result |
|---|---|---|
| P1, open 1 h | in progress, 50 %, `task_has_breached` true | **Breached** |
| P1, open 30 h | in progress, 60 %, planned end 1 h ago, `task_has_breached` false | **Breaching** (the flag decides a breach) |
| P2, open 30 h | cancelled, flagged breached · in progress, 10 % | **Within SLA** (the cancelled record is ignored) |
| P2, open 9 h | in progress, 40 % | **Within SLA** |
| P3, open 50 h | completed, not breached | **Met** |
| P1, open 2 h | none | **No SLA record** |
| P2, open 20 h, latest record On Hold | in progress, flagged breached | not listed (On Hold) |

All seven are cases in the local test data that the dashboard query is checked against
(`tools/test_mim_v3_2026-10-27s.py`).

## 7. Things to know

- **Time window.** Section 1 is fixed to the last 7 days. An SLA record whose `@timestamp` (when it was last synced)
  is older than that is not read. In-progress SLA records are re-synced every few minutes, so this only matters if
  the sync stops.
- **Dashboard filters.** A filter added from a click (e.g. *Filter for* on an incident) also applies to the SLA
  records. They have no incident `number` field, so the panel shows "No SLA record" while that filter is on. Remove
  the filter to see the real SLA again. The CI and Incident controls do not affect this panel.
- **Fields not used.** The incident record has its own SLA fields (`has_breached_sla`,
  `sla.primary.task_has_breached`, `sla.response.task_has_breached`), but they are empty on all P1 / P2 incidents
  for the last year (check S1 in *MIM-V3-DATA-CHECK-QUERIES.md*), so the separate SLA records are used instead.
- **Breaching thresholds** (75 % used, 30 minutes to planned end) are dashboard settings and can be changed.
