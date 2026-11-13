# Queries to run (13 Nov 2026)

For the MIM V5 *P1 / P2 / P3 Time to Resolve vs Target* fix (option A: real time to resolve). Run both in
**Dev Tools** and upload the results as `ttr.txt`.

## TTR1. Do resolved incidents carry their resolved time?

One row per priority, last 7 days.

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND @timestamp >= NOW() - 7 days AND TO_INTEGER(priority) IN (1, 2, 3)
| EVAL has_resolved = CASE(resolved_at IS NOT NULL, 1, 0), has_closed = CASE(closed_at IS NOT NULL, 1, 0),
       resolved_inc = CASE(resolved_at IS NOT NULL, number)
| STATS incidents = COUNT_DISTINCT(number), records = COUNT(*),
        records_with_resolved_at = SUM(has_resolved), records_with_closed_at = SUM(has_closed),
        incidents_with_resolved_at = COUNT_DISTINCT(resolved_inc), states = VALUES(TO_STRING(state_name))
  BY priority
| SORT priority
"""
}
```

## TTR2. Preview of the new chart

Average hours from opened to resolved, for incidents resolved each day, by priority.

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND resolved_at >= NOW() - 7 days AND TO_INTEGER(priority) IN (1, 2, 3)
| STATS resolved = MAX(TO_DATETIME(resolved_at)), opened = MIN(TO_DATETIME(opened_at)), pri = MIN(TO_INTEGER(priority)) BY number
| EVAL hours = DATE_DIFF("minutes", opened, resolved) / 60.0
| STATS incidents = COUNT(*), avg_hours = ROUND(AVG(hours), 1), max_hours = ROUND(MAX(hours), 1)
  BY day = DATE_TRUNC(1 day, resolved), pri
| SORT day, pri
| LIMIT 100
"""
}
```

## What the results tell us

- **TTR1 fails with "Unknown column [resolved_at]", or `incidents_with_resolved_at` is close to 0:** the resolved
  time is not in Elastic; we then check whether `closed_at` can stand in for it.
- **TTR2 returns sensible hours per day and priority:** the new chart is built on exactly that logic, with the
  4 h / 8 h / 24 h target lines kept.
- TTR2 also shows how many incidents are resolved each day per priority: if P1s are rare, their line will have gaps,
  which is normal.
