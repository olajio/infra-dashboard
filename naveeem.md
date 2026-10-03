Pulling the new image and looking at it.

I've read the image. Before designing, I'm checking what we already know about the data each block needs. First, the preview helpers from earlier mock-ups:

I'll check the existing exports to see how host metrics carry the CI, which fields the synthetics and logs panels use, and whether there's any process, middleware, or SLO data available.

Two more details: how the server metrics carry CI fields, and which fields the SQL Server and synthetics dashboards key on:

I'll mock this up following Naveen's layout, adding chips to each panel to show if data is ready, needs a sample, or isn't yet in Elastic, plus numbered badges indicating the review order.

I've spotted a few issues: overlapping labels on the change timeline, incorrect dates on the time-series axis, a clipped status chip in the narrow middleware panel, and a clipped Count column in the logs table. I'll fix each of these now.

One chip is still cut off, on the logs panel. Dropping that panel's subtitle to make room:

The cropped check failed (the crop area was outside the browser window), but the full-page render saved first. Checking it:

I've sent a mock-up of Naveen's layout with made-up data; nothing is built yet. Each panel has a chip showing whether its data is ready, and the numbers 1–6 follow the walkthrough below.

## How I read the sketch

The dashboard has two halves.
- **The top half covers every major incident.** It shows how many P1/P2s there are, how old they are, which CIs they sit on, what state they're in, and the full list.
- **The bottom half investigates one CI.** You pick a CI with the CI Filter (or by clicking one in the table), and every panel below shows that CI only: infrastructure, applications, processes, middleware/DB, synthetic checks, logs, SLO burn and recent changes.

The top half answers "what's going on". The bottom half answers "why, how bad, and who do we call".

## How a MIM lead would use it

1. **Spot the incident.** Look at the trend for a spike. *By CI* shows whether several incidents land on one CI, which usually means one underlying failure. *By age* and *by state* show what's stale or still New.
2. **Pick it.** In the incident table, read the SLA, the "why" and the assignment group, then click the Affected CI. The bottom half now shows that CI.
3. **Measure the impact.** Count the applications on the CI and check their health. SLO burn rate shows how fast customers are using up the error budget. Synthetics show whether the service looks down from outside.
4. **Confirm it's this CI.** Infrastructure health (CPU, memory, disk, whether it's reporting) and middleware/DB health show whether the CI itself is sick or something it depends on is.
5. **Find the cause.** The changes timeline shows whether a change, release or maintenance window landed just before the incident opened. Log errors and process health show what actually broke (for example, SQL Server stopped, then the application got connection timeouts).
6. **Escalate.** With impact and a likely cause in hand: declare a major incident if several applications are hit or the burn rate is past the "page now" level, open a bridge, and engage the CI's support group and the team that made the change.

I added an **Escalate** strip (step 6) that isn't in Naveen's sketch. It shows the CI's support group and its manager, with links to the CI and the incident in ServiceNow. Our change data already carries the group and manager, so you have the contacts without leaving the page. Keep it or drop it.

## Data status per panel

| Panel | Status | What we have / need |
|---|---|---|
| Time series, by age, by CI, by state, incident table | **Ready** | `servicenow-incidents`, plus the SLA and attention logic built last round |
| Infrastructure health | **Ready, one check** | Server metrics already carry CMDB fields per host. I need to confirm the host name matches the incident's CI name, e.g. `KAU1S054` vs `kau1s054`. |
| Changes | **Ready** | `servicenow-change-requests` |
| Releases, maintenance windows, CIs linked to the affected CI | **Not seen in Elastic** | Planned-outage fields were empty in the change sample; no release source seen; relationships need the CMDB tables |
| Applications on this CI | **Needs a sample** | `cmdb_app_dependencies_v2` (8.9k records) looks right but we've never seen its fields |
| Logs, process health, middleware/DB, synthetics | **Needs a sample** | Indices exist (Windows services, SQL Server metrics, IBM MQ, syslog / Windows / APM error logs, 1.8B synthetic checks), but I don't know which carry a CI or host field |
| SLO error burn rate | **Needs an answer** | Are SLOs set up in Kibana? If not, I'd calculate burn from APM against a target (e.g. 99.5 %) |

## Queries to run

Please run these in Discover (ES|QL mode) and upload the CSVs like last time. For queries 1 and 2, set the time picker to the last 15 minutes to keep them cheap; Last 1 year is fine for the rest.

1. Which metrics carry a CI:
   ```
   FROM metrics-* | WHERE ci.name IS NOT NULL | STATS docs = COUNT(*), hosts = COUNT_DISTINCT(host.name) BY data_stream.dataset | SORT docs DESC | LIMIT 50
   ```
2. Which logs can be filtered by host or CI, and have a level:
   ```
   FROM logs-* | STATS docs = COUNT(*), with_host = COUNT(host.name), with_ci = COUNT(ci.name), with_level = COUNT(log.level) BY data_stream.dataset | SORT docs DESC | LIMIT 50
   ```
   If this one errors on `ci.name`, drop the `with_ci` part.
3. Host versus CI name on the server metrics:
   ```
   FROM metrics-system.cpu-* | KEEP host.name, ci.name, ci.class_name, ci.support_group.l2.name | LIMIT 10
   ```
4. Samples, each `| LIMIT 5`:
   - `FROM cmdb_app_dependencies_v2`
   - `FROM synthetics-*`
   - `FROM metrics-windows.service-*`
   - `FROM metrics-system.process-*`

   An "unknown index" error on any of them is also an answer.

## Questions

1. **New dashboard or replace?** I suggest building this as **MIM V3** and leaving V2 as it is.
2. **"Impacted CI" in the sketch.** Under your team's definitions, Affected means the CI the incident is raised against, and Impacted means the CIs downstream of it. Does "Infrastructure Health (impacted CI)" mean the affected CI? And for changes "linked to the impacted CI", is the CI's cluster or parent, plus the apps it runs, enough?
3. **CI filter behaviour.** I'd use a normal, clearable control, and show "Pick a CI" prompts when nothing is selected. Agreed?
4. **SLOs.** Are SLOs set up in Kibana? If not, what availability target should I use per service?
5. **Releases and maintenance windows.** Where are they recorded? In ServiceNow (a change type, or maintenance schedules), Azure DevOps / Jenkins, or nowhere yet?
6. **Middleware / DB donut.** I assumed the slices are healthy / degraded / down components on or linked to the CI. Is that right?
