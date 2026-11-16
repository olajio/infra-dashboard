# Queries to run (16 Nov 2026)

For the items in `mim_recap.txt`. Run each in **Dev Tools** and upload the results as `recap_results.txt`.
(The TTR1 / TTR2 checks of 13 Nov are done: results in `ttr.txt`.)

## R1. What is "PBA"? Is there a PBA field in the ServiceNow data?

```
GET servicenow-*/_field_caps?fields=*pba*,*PBA*,*Pba*&filter_path=fields
```

If R1 returns a field, run this with its name in place of `FIELD`, to see its values on P1 / P2 incidents:

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

## R2. How old are the CMDB links? (to choose the time range of the alert panels)

The alert panels show "Last 5 years" because they also read CMDB links (`cmdb-ci-relations`), and a panel's time range
filters every index it reads. R2 shows whether the links are re-sent often enough for a shorter range.

```
POST /_query?format=txt
{
  "query": """
FROM cmdb-ci-relations*
| WHERE @timestamp >= NOW() - 5 years
| EVAL age = CASE(@timestamp >= NOW() - 1 day, "a: last 24 h", @timestamp >= NOW() - 7 days, "b: 1-7 days",
                  @timestamp >= NOW() - 30 days, "c: 7-30 days", "d: older than 30 days"),
       link = CONCAT(TO_STRING(parent.name), " | ", TO_STRING(child.name))
| STATS records = COUNT(*), links = COUNT_DISTINCT(link), newest = MAX(@timestamp), oldest = MIN(@timestamp) BY age
| SORT age
"""
}
```

## R3. MTTR for P1

No P1 was resolved in the 7 days the Time to Resolve chart covers (TTR1: one P1, On Hold). R3 looks back 90 days.

**R3a. Every P1 resolved in the last 90 days, with its time to resolve**

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND TO_INTEGER(priority) == 1 AND resolved_at >= NOW() - 90 days
| STATS opened = MIN(TO_DATETIME(opened_at)), resolved = MAX(TO_DATETIME(resolved_at)),
        ci = VALUES(TO_STRING(ci.name)), state = VALUES(TO_STRING(state_name)) BY number
| EVAL hours = ROUND(DATE_DIFF("minutes", opened, resolved) / 60.0, 1)
| SORT resolved DESC
| LIMIT 100
"""
}
```

**R3b. P1 MTTR: count, median and average, by month**

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND TO_INTEGER(priority) == 1 AND resolved_at >= NOW() - 90 days
| STATS opened = MIN(TO_DATETIME(opened_at)), resolved = MAX(TO_DATETIME(resolved_at)) BY number
| EVAL hours = DATE_DIFF("minutes", opened, resolved) / 60.0
| STATS incidents = COUNT(*), median_hours = ROUND(MEDIAN(hours), 1), average_hours = ROUND(AVG(hours), 1),
        max_hours = ROUND(MAX(hours), 1) BY month = DATE_TRUNC(1 month, resolved)
| SORT month
"""
}
```

## R4. The P2 duration calculated in ServiceNow

ServiceNow's incident table usually holds it as **duration** (`calendar_duration`, `calendar_stc`) and **business
duration** (`business_duration`, `business_stc`). R4a finds what reaches Elastic; R4b shows the values on a few
resolved P2s next to opened / resolved.

**R4a. Duration fields in the ServiceNow data**

```
GET servicenow-*/_field_caps?fields=*duration*,*stc*,*time_worked*,*resolve_time*,*business*&filter_path=fields.*.*.type
```

**R4b. Three resolved P2 incidents, with every duration-like field**

```
GET servicenow-incidents-*/_search?size=3&sort=@timestamp:desc&_source_includes=number,priority,state_name,opened_at,resolved_at,closed_at,*duration*,*stc*,*time_worked*,*resolve_time*
{ "query": { "bool": { "filter": [ { "term": { "priority": 2 } }, { "exists": { "field": "resolved_at" } } ] } } }
```

If R4a finds nothing, the duration is not sent to Elastic: ask the ServiceNow team to add the field
(`calendar_duration` or `business_duration`) to the incident feed.
