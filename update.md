# MIM V3 — progress update

- Split the Active P1 / P2 / P3 donut into three count panels: Active P1 (all), P2 over 8 h and P3 over 24 h (active past their target).
- Active Incidents now lists only those incidents.
- Changed the counts, Time to Resolve vs Target, Active Incidents and Escalate to look back 7 days instead of 1 month.
- SLA column in Active Incidents now shows Breached only from ServiceNow's `task_has_breached` flag (no longer estimated from incident age); incidents with no SLA record show "No SLA record".
- On Hold, Resolved, Closed and Canceled incidents removed from Active Incidents, the count panels and the Time to Resolve vs Target graph (the graph now shows only New and In Progress incidents).
- Investigated the "No SLA record" results: the dashboard reads the correct SLA index (`servicenow-task-sla`), but only about 3 % of incidents have an SLA record there. Pending confirmation from the ServiceNow team whether this is an integration gap or incidents without an SLA in ServiceNow.
- Found that the incident index's `@timestamp` is the opened time, so the 7-day panels show incidents opened in the last 7 days; incidents open longer drop out.
