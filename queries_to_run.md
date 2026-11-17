# Queries to run (17 Nov 2026)

Run in **Dev Tools** and upload the results as `recap_results3.txt`.

Done: R1 (no PBA field reaches Elastic), R2, R3, R4a–R4d. R4c / R4d showed `duration` and `business_duration` are
**not** on `servicenow-incidents-*`: R4a found them in another `servicenow-*` index. R4e finds which one.

## R4e. Which ServiceNow index holds `duration` / `business_duration`, and what is in it?

```
POST /_query?format=txt
{
  "query": """
FROM servicenow-* METADATA _index
| WHERE @timestamp >= NOW() - 30 days AND (duration IS NOT NULL OR business_duration IS NOT NULL)
| STATS records = COUNT(*), newest = MAX(@timestamp) BY _index
| SORT records DESC
| LIMIT 20
"""
}
```

## R4f. Three of those records, whole (to see what the duration belongs to: the incident, or an SLA)

Replace `INDEX` with the first index R4e lists.

```
GET INDEX/_search?size=3&sort=@timestamp:desc
{ "query": { "exists": { "field": "duration" } } }
```
