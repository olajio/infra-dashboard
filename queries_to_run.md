# Queries to run (17 Nov 2026)

For James Patock's proposal (`MIM SLA update.docx`): P1 MTTR from the ServiceNow **Outage** record, Duration for all
other priorities. Run in **Dev Tools** and upload the results as `outage_results.txt`.
(Done: R1–R4f; R4e / R4f showed `duration` lives only on the SLA records in `servicenow-task-sla`.)

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
