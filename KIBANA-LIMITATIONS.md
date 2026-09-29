# Kibana limitations — Operations dashboard family

What Kibana can't do, or can only do with a workaround, as found while building the Operations
dashboard and its detail dashboards. The environment is **Kibana 9.3**, with almost every panel
built as an **ES|QL Lens** chart.

Each item says how we know it:

- **Confirmed in source**: read in Kibana 9.3's own code.
- **Observed**: hit on this project and tested.
- **Not verified**: we didn't rely on it, so treat it as unknown until someone tests it.

Section 8 lists the data gaps, which aren't Kibana limitations, because they are often mistaken
for them.

---

## At a glance

| # | Limitation | What it means for us | Workaround in place |
|---|---|---|---|
| 1 | Dark / light theme is a per-viewer setting | The dashboard can't force the dark look the client liked | Each viewer sets Profile → Appearance → Dark |
| 2 | No custom CSS, HTML or fonts | Cards, spacing and fonts are Kibana's own | Layout, colour and chart choice carry the design |
| 3 | No sparkline column or data bars inside tables | The mock-up's "Trend" column can't be built | Trend lines sit beside the tables as separate charts |
| 4 | Donut charts can't show a total in the centre | The "98.5 %" centre label in the mock-up isn't possible | Legend shows count and % per slice |
| 5 | Drilldowns belong to the panel, not the column | A link on one column appears on every clickable column | Non-link columns are made non-clickable |
| 6 | A drilldown only knows the cell you clicked | Can't build a link from two columns of the same row | Link on one field only (CI name, incident number) |
| 7 | "Encode URL" double-encodes `%XX` in templates | Pre-encoded ServiceNow links break | Encode URL off for templates that contain `%XX` |
| 8 | ES\|QL has no window functions or "latest value per group" | Trends and "current state" need workarounds | Packing trick on the availability trend; grouping on identity only |
| 9 | ES\|QL can't walk a relationship graph | Impacted (downstream) CIs can't be computed on the dashboard | Needs an ENRICH policy or transform in Elasticsearch |
| 10 | Links between dashboards break if the target isn't imported | Detail-dashboard links 404 in a space that lacks them | Import all five dashboards into the same space |
| 11 | Colour rules match whole values only | A rule for "🔴" doesn't colour "🔴 RED"; everything falls back to grey | One rule per exact status text |
| 12 | A tile's colour can only follow its own number | A RAG built from incidents *and* availability can't colour the tile directly | Hidden "max" column steers the colour (§2) |
| 13 | Area and bar charts always start the y-axis at 0 | A 99–100 % availability trend flattens into a solid block | Availability trends are line charts with a tight axis |
| 14 | `metrics-*` mixes field types across indices | ES\|QL refuses a query that reads a field typed differently in two indices | Query the specific data stream instead |

---

## 1. Look and feel

**Theme is per viewer, not per dashboard.** *(Observed)*
Dark mode is a user-profile preference: Profile → Appearance. A dashboard export has no field for
it, so the same dashboard renders light for anyone who hasn't switched. If the dark look matters for
a presentation, set it on the presenting account beforehand.

**No custom styling.** *(Observed)*
Markdown panels are sanitised: no HTML, no CSS, no custom fonts. Card borders, corner radius,
shadows and typography are fixed by Kibana's design system. The things we *can* control are layout,
colour (on values and tables), chart type, titles, subtitles and panel descriptions (the ⓘ icon).

**Colours are fixed hex values.** *(Observed)*
Status colours on tiles and tables are stored as fixed hex codes and don't adapt to the viewer's
theme. We chose red `#d6453d`, amber `#c98a0b` and green `#1f9e6b` because they read on both dark
and light. Amber is the weakest on a white background, so every status also carries a 🔴 / 🟠 / 🟢
emoji or a label; colour never carries the meaning on its own.

---

## 2. Charts and tiles

**Metric tiles.** *(Confirmed in source)*
A tile can show a subtitle, a secondary value, a progress bar and value-based colouring on the number
or the background. Two things need extra work:

- **Progress bar.** It needs a "maximum" column in the query. Four tiles carry a constant
  `EVAL max_val = 1.0` for this reason; it is display-only.
- **Text value.** A tile can show a text value such as 🔴 RED, but value-based colouring only works on
  numbers. The Overall Infrastructure Health tile is therefore coloured by its emoji, not by the tile
  palette.

**"vs last period" deltas.** *(Confirmed in source)*
Kibana can compare a tile's secondary value to its primary one and draw the ↑ / ↓ badge. It can't
fetch last period's value by itself, so each delta would need its own ES|QL logic computing the
previous window. It's possible but was left out; it's a query change on every tile.

**Donut charts.** *(Observed)*
There's no centre label. Totals and percentages appear in the legend and on the slices instead.

**A tile's colour can only follow its own number.** *(Confirmed in source)*
Colour-by-value reads the tile's primary number, and only if it is a number. Overall Infrastructure
Health is RED / AMBER / GREEN from open P1s and P2s *as well as* CI availability, while the tile
displays CI availability. The workaround: when a tile has a "max" column, Kibana colours it by
value ÷ max, so a hidden max column is set to land that ratio at 20 % (red), 50 % (amber) or 90 %
(green) according to the RAG the query already computes. The number shown is untouched. If anyone
edits this tile, keep the max column and the percent-based palette together.

**Area and bar charts always include zero on the y-axis.** *(Observed)*
Kibana only allows a data-bounded y-axis on line charts. An availability trend between 99 % and
100 % drawn as an area therefore looks like a flat block. Availability trends stay line charts with
the axis fitted to the data; area is kept for volumes that naturally start at zero.

**Trend granularity follows the query, not the time picker.** *(Observed)*
Our three original trends bucket by hour. At the saved 4-hour window, that is 3–4 points per line.
The Resource Utilisation trend uses `BUCKET(@timestamp, 48, ?_tstart, ?_tend)`, which adapts
to the picker. On our version `BUCKET()` is only accepted inside `STATS … BY` (for example
`BY bucket = BUCKET(…)`); in an `EVAL` the query fails with *"cannot use grouping function outside
of a STATS"*. The P1/P2 trend stays hourly on purpose, because ServiceNow snapshot frequency is
unconfirmed and finer buckets could show false dips.

---

## 3. Tables

**No inline sparklines or data bars.** *(Observed)* A table cell holds text or a number, optionally
coloured. Nothing graphical.

**Colouring works, with two different mechanisms.** *(Confirmed in source)*

- **Numbers** are coloured by threshold. We colour CPU, memory, disk, error-rate and minutes-stale
  columns using each panel's own thresholds.
- **Text** is coloured by matching its value, and **only whole values match**. In Kibana 9.3 a rule
  for `🔴` does not colour `🔴 RED`; partial-match rules are silently ignored and every value falls
  back to grey. This is what turned the Application Health Mix donut grey. Every status column and
  donut now carries one rule per exact status text. **If a query's status wording changes, its
  colour rule must change with it.**

**Row limits.** *(Observed)* ES|QL returns 1,000 rows by default and 10,000 at most. Our worklists
use explicit `LIMIT 100` and paginate.

---

## 4. Clicks, filters and drilldowns

**Drilldowns are per panel, not per column.** *(Observed)*
Every URL drilldown on a table fires from every clickable column. The only way to confine a link to
one column is to make the other columns non-clickable (`inMetricDimension` on the column). Wrapping a
value in `TO_STRING()` does **not** do it.

**A drilldown only sees the clicked cell.** *(Observed)*
`{{event.value}}` and `{{event.points}}` carry the value you clicked, not the rest of the row. A URL
needing two fields from one row, such as ServiceNow's class-scoped CMDB link (`ci.class` +
`ci.sys_id`), can't be built from a click. We link on CI name instead.

**"Encode URL" double-encodes.** *(Observed)*
Kibana percent-encodes the finished URL, so a template that already contains `%3F` or `%3D` becomes
`%253F`. This broke three attempts at the CMDB link before it was found. Rule of thumb:

- **Template contains `%XX`:** turn Encode URL off.
- **Template has no `%XX` and the value may contain spaces:** leave it on.

**Clicking computed columns doesn't filter usefully.** *(Observed)*
A click adds a dashboard filter on that column's field. If the column was created in the query with
`EVAL`, that field doesn't exist in the index, so other panels can't use the filter. Clicks on real
fields (host name, CI name, incident number) work as expected.

---

## 5. ES|QL (the query language)

**No window functions and no "latest value per group".** *(Observed)*
There is no `LAG`, no running total and no "last reading per host". The Server Availability trend
works around this by packing timestamp and value into one number and unpacking it. Anything needing
"the most recent value" has to be approximated with `MAX` / `MIN` over a short window.

**Group on identity, never on descriptive attributes.** *(Observed; a pitfall rather than a missing
feature)*
If a CMDB attribute such as environment or support group changes mid-window, grouping by it splits
one server into two rows, and the older row looks "down". This caused phantom down servers three
times. Group on `host.name` or `ci.name` and collapse attributes with `VALUES()` + `MV_MAX()`.

**No graph traversal.** *(Observed)*
Impacted CIs, the downstream dependents of an affected CI, live in `cmdb-ci-relations-000002`
(33.9M edges). ES|QL can't walk that graph at query time. Closing it is an Elasticsearch change,
an ENRICH policy or a denormalising transform, not a dashboard change.

**The same field can have different types in different indices.** *(Observed)*
`metrics-*` also matches legacy Metricbeat indices where `system.cpu.total.norm.pct` is a
`scaled_float`, while the current data streams map it as `double`. ES|QL refuses to read a field with
conflicting types, so the whole panel errors. Query the specific data stream, as the saturation
tables and the Resource Utilisation trend now do (`.ds-metrics-system.cpu-default*`).

**Snapshot indices repeat every record.** *(Observed; a pitfall rather than a missing feature)*
`servicenow-open-incidents-snapshots-*` stores a fresh copy of each incident at every snapshot. A
plain `WHERE state_name != "Resolved"` still counts an incident resolved an hour ago, because its
earlier "In Progress" snapshots are in the window. Active-incident panels must judge each incident
on its **latest** snapshot: `MAX(TO_LONG(@timestamp) * 10 + value) % 10` returns the latest small
integer (state flag, priority) per incident without a join.

**Mapped doesn't mean populated.** *(Observed)*
Field lists and `field_caps` show what's mapped, not what holds data. Many ServiceNow and Oracle
fields are mapped but empty. Always check with `COUNT(field)` before building on a field.

---

## 6. Saved objects and deployment

**Each dashboard is its own import.** *(Observed)*
The landing page and the four detail dashboards are separate NDJSON files. Links between them use
the saved-object id, for example `/app/dashboards#/view/db-detail-mssql-v1`, so a link opens nothing
unless that dashboard is imported **into the same space**.

**Short links are instance-specific.** *(Observed)*
The `/app/r/s/…` links in the top bar resolve only on the Kibana instance that created them.

**Collapsible sections need a recent Kibana.** *(Confirmed in source)*
They are part of the 9.x dashboard format (`sections` plus `gridData.sectionId`). Older Kibana
versions will not show them.

**Import with "overwrite".** *(Observed)*
Import with *Check for existing objects* and overwrite, so the dashboard keeps its id, URL and
bookmarks.

---

## 7. Not verified — test before promising

We didn't use these, so we have no evidence either way. Test them in our Kibana before committing to
them in front of the client.

- **Sparklines inside metric tiles for ES|QL panels.** Kibana supports tile trendlines, but we didn't
  confirm they work on ES|QL-based tiles, which is most of ours.
- **Gauges (arc, semicircle, bullet) driven by ES|QL.**
- **Target / reference lines on ES|QL line charts** (for example a dashed 99.9 % line).

---

## 8. Not Kibana: data gaps that look like Kibana limits

Worth separating in any conversation, because none of these is fixed by a better dashboard.

| Gap | Cause | Fix belongs to |
|---|---|---|
| MTTA (time to acknowledge) | No acknowledge / assign timestamps on ServiceNow incidents | ServiceNow business rule + integration mapping |
| SLA breach | SLA data sits in `servicenow-task-sla`, not on the incident | Wire that index in |
| Oracle metrics | Collectors fail with `DPI-1047`: Oracle Instant Client missing on 2 hosts | Install the client on `lrch1e01` and `vslrau1p298` |
| ~255 of 390 SQL Server instances | Monitoring login is failing | Fix the service account credentials |
| Netcool alert severity breakdown | No severity field confirmed on the Netcool index | Confirm the field, then add the panel |
| Impacted (downstream) CIs | Needs the CMDB relationship graph | ENRICH policy or transform (§5) |
| Noise-reduction opportunity score | No rule id, dedup outcome or analyst-feedback fields | Netcool / ServiceNow data changes |
