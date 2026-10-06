# MIM V3: how the SLA column is calculated

**Panel:** *Active Incidents (P1 / P2)*, section 1 of MIM V3 · **Column:** SLA

The SLA column shows the **worst SLA on each incident**. It uses ServiceNow's own SLA records whenever the incident
has them. Only when an incident has no SLA record does the dashboard estimate from the incident's age, and those
values are marked **(age)**.

---

## 1. Where the data comes from

| Index | What it gives | Key fields |
|---|---|---|
| `servicenow-incidents-*` | The incident: priority, state, opened time | `number`, `priority`, `state_name`, `opened_at` |
| `servicenow-task-sla-*` | One record per SLA attached to an incident (response, resolution …) | `task_number` (= incident number), `stage`, `task_has_breached`, `percentage`, `planned_end_time`, `contract_name` |

The two are matched on **incident number** (`number` = `task_number`). An incident usually has two SLA records: a
**Response** SLA and a **Resolution** SLA. The dashboard treats a record as a Response SLA when its `contract_name`
contains "respon", and as a Resolution SLA otherwise.

Only **active P1 / P2** incidents are listed: priority 1 or 2 and state not Resolved, Closed, Canceled or Cancelled.

## 2. Step 1: rate each SLA record

Each SLA record gets one status. The rules are checked in this order, and the first match wins.

| Rank | Status | Rule (on the SLA record) |
|---|---|---|
| 1 | **Breached** | `task_has_breached` is true, **or** `stage` is `breached`, **or** `stage` is `in_progress` and `planned_end_time` has already passed |
| 2 | **Breaching** | `stage` is `in_progress` **and** either `percentage` ≥ **75 %** or `planned_end_time` is within the next **30 minutes** |
| 3 | **Paused** | `stage` is `paused` (the incident is On-Hold, so the SLA clock is stopped) |
| 4 | **Within SLA** | `stage` is `in_progress`, with no rule above matching |
| 5 | **Met** | Any other stage, such as `completed`, without a breach |
| — | *(ignored)* | `stage` is `cancelled` |

Why the planned end time is checked as well as the flag: ServiceNow updates `task_has_breached` and `percentage`
on a schedule, so they can lag behind. A planned end time in the past means the SLA has breached even if the flag
has not caught up yet.

## 3. Step 2: one SLA per incident (the worst one)

The incident shows the **lowest rank** among its SLA records, which is the worst status. For example, if the
Response SLA is Breached and the Resolution SLA is Within SLA, the incident shows **Breached**.

## 4. Step 3: no SLA record, so estimate from age

If an incident has no (non-cancelled) SLA record, its age since `opened_at` is compared with a target:

| Priority | Target |
|---|---|
| P1 | 4 hours |
| P2 | 8 hours |

| Status | Rule |
|---|---|
| **Breached (age)** | Age ≥ target |
| **At risk (age)** | Age ≥ 80 % of target (P1 from 3 h 12 min, P2 from 6 h 24 min) |
| **Within SLA (age)** | Otherwise |

The 4 h / 8 h targets are dashboard defaults, not values read from ServiceNow. Please confirm they match CNA's P1 /
P2 resolution targets. They are one number each in the query, so they are easy to change.

## 5. Colours

| Status | Colour |
|---|---|
| Breached, Breached (age) | Red |
| Breaching, At risk (age) | Amber |
| Paused | Grey |
| Within SLA, Within SLA (age), Met | Green |

## 6. Worked examples

| Incident | SLA records | Result |
|---|---|---|
| P1, open 1 h 12 min | Response: in progress, 131 %, planned end 10 min ago · Resolution: in progress, 30 % | **Breached** (Response SLA past its planned end) |
| P2, open 3 days | Resolution: in progress, 82 % | **Breaching** (≥ 75 % used) |
| P2, New | Resolution: paused, 41 % | **Paused** |
| P2, open 5 h | Response: completed · Resolution: in progress, 40 % | **Within SLA** (completed = rank 5, in progress = rank 4; worst is 4) |
| P1, open 30 min | none | **Within SLA (age)** (30 min < 3 h 12 min) |
| P1, open 3 h 30 min | none | **At risk (age)** |
| P2, open 9 h | none | **Breached (age)** |

The first five rows are cases in the local test data that the dashboard query is checked against. The last two
follow from the same rules.

## 7. Things to know

- **Time window.** Section 1 is fixed to the last month. An SLA record whose `@timestamp` (when it was last synced)
  is older than that is not read, and the incident then falls back to the age rule. If you see "(age)" on an
  incident that has an SLA in ServiceNow, check when that SLA record was last synced to Elastic.
- **Dashboard filters.** A filter added from a click (e.g. *Filter for* on an incident) also applies to the SLA
  records. They have no incident `number` field, so the panel shows "(age)" while that filter is on. Remove the
  filter to see the real SLA again. The CI and Incident controls do not affect this panel.
- **Fields not used.** The incident record has its own SLA fields (`has_breached_sla`,
  `sla.primary.task_has_breached`, `sla.response.task_has_breached`), but they are empty on all P1 / P2 incidents
  for the last year (check S1 in *MIM-V3-DATA-CHECK-QUERIES.md*), so the separate SLA records are used instead.
- **Breaching thresholds** (75 % used, 30 minutes to planned end) are dashboard settings and can be changed.
