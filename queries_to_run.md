# Queries to run (16 Nov 2026)

Run in **Dev Tools** and upload the results as `recap_results2.txt`.
Done: R2 (`r2.csv`), R3 and R4a / R4b (`recap_results.txt`). The R1 result was not in `recap_results.txt`.

## R1. What is "PBA"? Is there a PBA field in the ServiceNow data?

```
GET servicenow-*/_field_caps?fields=*pba*,*PBA*,*Pba*&filter_path=fields
```

An empty result (`{}`) means no field named PBA reaches Elastic. If it returns a field, run this with its name in
place of `FIELD`:

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND @timestamp >= NOW() - 30 days
| STATS incidents = COUNT_DISTINCT(number) BY value = TO_STRING(FIELD), priority
| SORT priority, incidents DESC
| LIMIT 50
"""
}
```

## R4c. Which P2 incidents carry the ServiceNow duration?

R4a found the fields `duration` and `business_duration` (stored as dates, ServiceNow's way of holding a length of
time), but the three resolved P2s in R4b had neither. ServiceNow usually fills them when an incident is **closed**.
R4c counts them by state.

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND TO_INTEGER(priority) == 2 AND @timestamp >= NOW() - 30 days
| EVAL has_duration = CASE(duration IS NOT NULL, 1, 0), has_business_duration = CASE(business_duration IS NOT NULL, 1, 0)
| STATS records = COUNT(*), incidents = COUNT_DISTINCT(number), with_duration = SUM(has_duration),
        with_business_duration = SUM(has_business_duration) BY state = TO_STRING(state_name)
| SORT state
"""
}
```

## R4d. The duration values, next to the opened → resolved time

`duration_hours` and `business_hours` read the dates as lengths of time; `resolve_hours` is opened → resolved, for
comparison.

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND TO_INTEGER(priority) == 2 AND duration IS NOT NULL
| EVAL duration_hours = ROUND(TO_LONG(duration) / 3600000.0, 1),
       business_hours = ROUND(TO_LONG(business_duration) / 3600000.0, 1),
       resolve_hours = ROUND(DATE_DIFF("minutes", TO_DATETIME(opened_at), TO_DATETIME(resolved_at)) / 60.0, 1)
| SORT @timestamp DESC
| KEEP number, state_name, opened_at, resolved_at, closed_at, duration, business_duration, duration_hours, business_hours, resolve_hours
| LIMIT 10
"""
}
```
