# Queries to run (17–18 Nov 2026)

For James Patock's proposal (`MIM SLA update.docx`): P1 MTTR from the ServiceNow **Outage** record, Duration for all
other priorities. Run in **Dev Tools** and upload the results as `outage_results.txt`.
(Done: R1–R4f; R4e / R4f showed `duration` lives only on the SLA records in `servicenow-task-sla`.
Done: O1–O3 (`outage_results.txt`): no Outage records in Elastic; the snapshots give the became-P1 time to within
a few minutes.
Done: O4 (`timeline_results.txt`): the timeline has priority, state, `updated_at` and `resolution_time` (seconds
from opened to resolved); the search matched INC2692216's ~2,500 child incidents, not the P1 itself.
Done: O5 (`timeline_results2.txt`): the timeline keeps every update with its priority, so the exact became-P1 time
is available (INC2692216: 20:10:13). `resolution_time` is also on the incident records. The second O5 query failed
because `first` is a reserved word in ES|QL; not needed now.)

## O1. Do ServiceNow Outage records reach Elastic?

```
GET _cat/indices/*outage*,servicenow-*?v&h=index,docs.count,creation.date.string&s=index
```

```
GET servicenow-*/_field_caps?fields=*outage*,*begin*,*end*,*u_*&filter_path=fields
```

## O2. When did a P1 become a P1? (the fallback if Outage records are not synced)

The open-incident snapshots keep each incident's priority over time; the first snapshot at priority 1 is about when it
became a P1. Shown for the last P1 (INC2692216, Email/Exchange PROD, 12–13 Nov).

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-open-incidents-snapshots-*
| WHERE TO_STRING(number) == "INC2692216"
| EVAL p1_at = CASE(TO_INTEGER(priority) == 1, @timestamp)
| STATS first_seen = MIN(@timestamp), became_p1 = MIN(p1_at), last_seen = MAX(@timestamp),
        priorities = VALUES(TO_INTEGER(priority)), opened = MIN(TO_DATETIME(opened_at)), snapshots = COUNT(*)
"""
}
```

## O3. How often are snapshots taken? (how precise O2 can be)

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-open-incidents-snapshots-*
| WHERE @timestamp >= NOW() - 2 hours
| STATS records = COUNT(*), incidents = COUNT_DISTINCT(number) BY t = DATE_TRUNC(5 minutes, @timestamp)
| SORT t DESC
| LIMIT 24
"""
}
```

## O4. Does the incident timeline record priority changes? (exact became-P1 time)

`servicenow-incident-timelines-000001` (10.3 M records) has not been looked at yet. If it logs each priority change
with its time, it gives the exact moment an incident became a P1, better than the snapshots. Upload the results as
`timeline_results.txt`.

```
GET servicenow-incident-timelines-000001/_search?size=0
{ "aggs": { "newest": { "max": { "field": "@timestamp" } } } }
```

```
GET servicenow-incident-timelines-000001/_mapping?filter_path=*.mappings.properties.*.type,*.mappings.properties.*.properties
```

```
GET servicenow-incident-timelines-000001/_search?size=20&q=INC2692216&sort=@timestamp:asc
```

## O5. The P1's own timeline records (is each priority change kept?)

O4's search matched the ~2,500 child incidents linked to INC2692216, not the P1 itself. These look at the P1's own
records and at whether the timeline keeps more than one priority per incident. Upload the results as
`timeline_results2.txt`.

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incident-timelines-000001
| WHERE number == "INC2692216"
| KEEP @timestamp, updated_at, priority, state_name, is_major_incident, opened_at, resolved_at, resolution_time
| SORT @timestamp ASC
| LIMIT 50
"""
}
```

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incident-timelines-000001
| WHERE opened_at >= NOW() - 90 days
| STATS records = COUNT(*), priorities = VALUES(priority), states = VALUES(state_name), first = MIN(@timestamp)
  BY number
| WHERE MV_MIN(priorities) == 1
| SORT first DESC
| LIMIT 20
"""
}
```

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incident-timelines-000001
| WHERE opened_at >= NOW() - 7 days
| STATS records = COUNT(*), incidents = COUNT_DISTINCT(number)
"""
}
```

```
GET servicenow-incidents-*/_field_caps?fields=resolution_time,is_major_incident,parent_incident.number&filter_path=fields
```

## F1. What changed in `cmdb_with_apm_flag`? (why Application Health started failing on 17–18 Nov)

The MIM dashboard in production is identical to the last version built (`mim_error.ndjson`), so the errors come from
the data: `cmdb_with_apm_flag` now has `ci.name` and `service.name` as text fields. These show when the index was
created (re-created = reloaded) and which fields it has now. Upload the results as `flag_results.txt`.

```
GET _cat/indices/cmdb_with_apm_flag?v&h=index,docs.count,creation.date.string
```

```
GET cmdb_with_apm_flag/_mapping
```

## T1. Is P2 Duration right? (the P2 points sit near 0.3 h)

For P2s resolved in the last 7 days: `resolution_time` (ServiceNow, seconds) against opened → resolved from the dates.
The two hour columns should match. Upload the results as `p2_duration.txt`.

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-incidents-*
| WHERE TO_STRING(number) LIKE "INC*" AND TO_INTEGER(priority) == 2 AND resolved_at >= NOW() - 7 days
| STATS opened = MIN(TO_DATETIME(opened_at)), resolved = MAX(TO_DATETIME(resolved_at)), rt = MAX(TO_INTEGER(resolution_time)) BY number
| EVAL rt_hours = ROUND(rt / 3600.0, 2), date_hours = ROUND(DATE_DIFF("minutes", opened, resolved) / 60.0, 2)
| STATS incidents = COUNT(*), median_rt_hours = MEDIAN(rt_hours), median_date_hours = MEDIAN(date_hours),
        under_1h = SUM(CASE(date_hours < 1, 1, 0)), no_rt = SUM(CASE(rt IS NULL, 1, 0))
"""
}
```
