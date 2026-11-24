**Subject: CMDB relationship data in Elastic: why dashboards show inconsistent results, and the fix**

## The problem

The CMDB relationship data in Elastic (`cmdb-ci-relations*`) records how CIs connect to each other: which servers, databases and middleware an application runs on.

Each relationship record carries a timestamp of when it was loaded. In Kibana, every panel only shows records whose timestamp falls inside the panel's time range. As a result, the relationships we see depend on the time range, not on what is true in the CMDB today:

- **Narrow time range (e.g. last 24 hours):** relationships loaded earlier are hidden. Panels like Application Health then show nothing for an incident, even when the application is related to the CI. We hit this recently with an eFile PROD incident.
- **Wide time range (e.g. last 5 years):** we also see relationships that no longer exist, such as a server that was decommissioned or moved off an application. Searching across years of data also puts unnecessary load on the cluster.

Neither setting gives a correct, current picture.

## Why it happens

The index is built like a log, where each load adds new records with a timestamp. CMDB relationships aren't events. They are a current state: a server either is or isn't related to an application right now.

## Proposed fix

Redesign the index to hold only the current relationships, with two changes:

1. **Remove the timestamp from the relationship records.** Panels then always show every current relationship, whatever time range is selected.
2. **Keep the index in sync with the CMDB.** When a relationship is removed in ServiceNow, it must also be removed from Elastic. Either approach works:
   - **Give each relationship a fixed ID** (for example, built from the two CIs and the relationship type). Each load updates the record instead of adding a copy, and the load job deletes records the CMDB no longer contains.
   - **Rebuild the index on each load:** clear out the old relationships and load the current set (in Elasticsearch, a "delete by query" followed by the new load).

## Benefits

- The dashboards show the CMDB as it is today: no missing relationships, no stale ones.
- Results no longer change with the time range, so teams can trust what they see during an incident.
- Lower cluster load, because queries read one current set of relationships instead of years of copies.
- The same applies to the CMDB application list (`cmdb_with_apm_flag`), which has the same design and the same problem.

## What we need

The team that loads the CMDB data into Elastic (ATOS) needs to make the index change and update the load job. Once it's in place, we'll remove the time-range workaround from the dashboards.
