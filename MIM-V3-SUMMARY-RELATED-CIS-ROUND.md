# MIM V3 — summary: related CIs without blind spots, one applications table, "Times fired" (16 Oct 2026)

All the requests from this round are done and pushed to main. To see the changes on the cluster: import
`MIM V3.ndjson` (overwrite), then **More → Reset changes** and reload. All tests pass on Kibana 9.5.3.

## Earlier in this round
- The summary of the 9.5.3 donut and Time to Resolve fix is in *MIM-V3-DONUT-AND-TREND-FIX-9.5.3.md*.
- The Middleware, Database, Server and Application views moved into *2 · Investigate the CI*, right after
  *Blast radius*. Sections 4 and 5 became 3 and 4.

## Why relationships you see in ServiceNow were missing

There were four causes:
1. **The wrong source.** The views and the application table read `cmdb_app_dependencies_v2`, which holds only part
   of the CMDB's relationships. They now read `cmdb-ci-relations*`, the full ServiceNow relationship graph
   (34.2 million links).
2. **Fixed class lists.** Anything outside the Middleware, Database, Server and Application classes appeared nowhere.
   A new table, **Other related CIs**, sits where *Application View* was and lists every other class: load balancer
   pools, clusters, VMs, network gear, disks and so on.
3. **Retired CIs were hidden.** They are now shown last, marked "· retired".
4. **Exact name matching.** A CI name stored in a different case was missed. Names now also match in UPPER and lower
   case. A name in mixed case (e.g. "Claim center PROD") is still missed, because matching any case would make each
   panel search all 34 million links.

These panels have a fixed **Last 5 years** range, because relationship records go back to 2023. With the default
24 hours most would be hidden.

## One application table: "Applications related to this CI"

It replaces both *Applications that depend on this CI* and *Application View*, and shows every application related
to the CI in both directions. The *How* column spells out which way each one goes, for example "Claim Center — it
consumes this CI" or "this CI depends on it". *Blast radius* now counts from the same data.

**Trade-off:** clicking the *Application* column no longer opens ServiceNow. Kibana 9.5 blocks that click when the
name can come from either side of a relationship. The views have always had the same limit.

## "Count" is now "Times fired"

In *Open Alerts with No Incident*, and in *Alerts on this CI* too, since it is the same value.

## To confirm there are no blind spots on your cluster

Part 5 of *MIM-V3-RELATED-CIS-NO-BLIND-SPOTS.md* has a query to run in Discover for one CI and compare with ServiceNow.
- Everything the query returns now appears on the dashboard. Only links marked for deletion in ServiceNow are left
  out.
- If ServiceNow shows a relationship the query does not return, it is missing from the relationship data itself.
  That is for the CMDB integration team, not the dashboard.

Tested on sample data around the *Claim Center PROD* example, not yet on the real CMDB.
